"""Import product photos from product-photos/ into media/products/.

Usage:
    .venv\\Scripts\\python.exe manage.py import_product_photos
    .venv\\Scripts\\python.exe manage.py import_product_photos --replace

Files must be named after the product, e.g. "Rainbow Stacking Rings.jpg".
Extra photos end with a space and number: "Rainbow Stacking Rings 2.jpg".
Matching ignores case, spaces, dashes and underscores.
"""
import io
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from store.models import Product, ProductPhoto


def _normalise(name):
    """Lowercase, strip extension, collapse spaces/dashes/underscores for fuzzy matching."""
    name = re.sub(r'\.[^.]+$', '', name)  # drop extension
    return re.sub(r'[\s\-_]+', '', name).lower()


def _parse_filename(stem):
    """Return (base_name, photo_number) from a file stem.

    "Rainbow Stacking Rings"   -> ("Rainbow Stacking Rings", 1)
    "Rainbow Stacking Rings 2" -> ("Rainbow Stacking Rings", 2)
    """
    m = re.match(r'^(.+?)\s+(\d+)$', stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 1


def _fix_exif_and_crop(path):
    """Open image, correct EXIF rotation, crop to centred square, resize to 1200x1200.

    Returns a BytesIO with the final JPEG at quality 85.
    """
    from PIL import Image, ExifTags  # noqa: PLC0415

    img = Image.open(path)

    # Fix phone rotation stored in EXIF
    try:
        orientation_key = next(
            k for k, v in ExifTags.TAGS.items() if v == 'Orientation'
        )
        exif = img._getexif()  # None for PNGs and images without EXIF
        if exif and orientation_key in exif:
            rotation_map = {3: 180, 6: 270, 8: 90}
            degrees = rotation_map.get(exif[orientation_key])
            if degrees:
                img = img.rotate(degrees, expand=True)
    except (AttributeError, StopIteration):
        pass

    # Centre-crop to square
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    # Resize
    img = img.resize((1200, 1200), Image.LANCZOS)

    # Ensure RGB (Pillow can't save RGBA/palette as JPEG)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85, optimize=True)
    buf.seek(0)
    return buf


class Command(BaseCommand):
    help = "Import product photos from product-photos/ into media/products/."

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete existing photos and re-import instead of skipping.',
        )

    def handle(self, *args, **options):
        replace = options['replace']
        photo_dir = settings.BASE_DIR / 'product-photos'

        if not photo_dir.exists():
            self.stdout.write(self.style.ERROR(
                f"Folder not found: {photo_dir}\n"
                "Create it and drop your photos in, then run this command again."
            ))
            return

        extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        files = [f for f in photo_dir.iterdir()
                 if f.is_file() and f.suffix.lower() in extensions]

        if not files:
            self.stdout.write(self.style.WARNING("No image files found in product-photos/"))
            return

        # Group files: base_name -> sorted list of (photo_number, path)
        groups: dict[str, list] = {}
        for f in files:
            base, n = _parse_filename(f.stem)
            groups.setdefault(base, []).append((n, f))
        for base in groups:
            groups[base].sort(key=lambda t: t[0])

        # Build product lookup: normalised name -> Product
        product_map = {_normalise(p.name): p for p in Product.objects.all()}

        # Separate matched from unmatched
        matched: dict[str, tuple] = {}   # base -> (Product, [(n, path), ...])
        unmatched: list[str] = []
        for base, photos in groups.items():
            key = _normalise(base)
            if key in product_map:
                matched[base] = (product_map[key], photos)
            else:
                unmatched.append(base)

        # Report unmatched files
        if unmatched:
            self.stdout.write(self.style.WARNING("\nFiles with no matching product — skipped:"))
            for name in sorted(unmatched):
                self.stdout.write(f"  ✗ {name}")

        # Report products with no photo file
        matched_keys = {_normalise(b) for b in matched}
        no_photo = [p.name for p in Product.objects.order_by('name')
                    if _normalise(p.name) not in matched_keys]
        if no_photo:
            self.stdout.write(self.style.WARNING("\nProducts with no photo in product-photos/:"))
            for name in no_photo:
                self.stdout.write(f"  - {name}")

        if not matched:
            self.stdout.write("\nNothing to import.")
            return

        self.stdout.write(f"\nImporting {len(matched)} product(s)…")
        imported = 0
        skipped = 0

        for base, (product, photos) in sorted(matched.items()):
            if not replace and product.image:
                self.stdout.write(f"  skip  {product.name}  (already has photo; use --replace)")
                skipped += 1
                continue

            if replace:
                if product.image:
                    product.image.delete(save=False)
                product.photos.all().delete()

            success = True
            for i, (n, path) in enumerate(photos):
                try:
                    buf = _fix_exif_and_crop(path)
                    suffix = f"_{n}" if n > 1 else ""
                    filename = f"{product.slug}{suffix}.jpg"

                    if i == 0:
                        product.image.save(filename, ContentFile(buf.read()), save=True)
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓  {product.name}  →  products/{filename}")
                        )
                    else:
                        photo_obj = ProductPhoto(
                            product=product,
                            alt=f"{product.name} photo {n}",
                            order=i,
                        )
                        photo_obj.image.save(filename, ContentFile(buf.read()), save=True)
                        self.stdout.write(f"       + extra photo {n}  →  {filename}")

                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗  {product.name} photo {n}: {exc}")
                    )
                    success = False

            if success:
                imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {imported} imported, {skipped} skipped."
        ))
