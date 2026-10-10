"""Zip-based bulk photo upload for products."""
import io
import re
import zipfile

from django.core.files.base import ContentFile

from .models import Product, ProductPhoto

ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "avif", "bmp", "tiff", "tif"}
MAX_ZIP_BYTES = 60 * 1024 * 1024  # 60 MB


def _normalize(s):
    return re.sub(r"\s+", " ", s.strip()).lower()


def _build_lookup():
    products = list(Product.objects.all())
    by_name, by_sku, by_slug = {}, {}, {}
    for p in products:
        by_name[_normalize(p.name)] = p
        if p.sku:
            by_sku[p.sku.lower().strip()] = p
        by_slug[p.slug.lower()] = p
    return by_name, by_sku, by_slug


def _match_product(folder_name, by_name, by_sku, by_slug):
    key = _normalize(folder_name)
    return by_name.get(key) or by_sku.get(key) or by_slug.get(key)


_VIDEO_EXTS = {"mp4", "webm", "mov", "m4v"}


def process_bulk_zip(zip_bytes, replace=False):
    """
    Process a zip file and import photos to matching products.

    Top-level folder → product matched by name (case-insensitive, collapse
    spaces), SKU, or slug. Images sorted alphabetically: first becomes
    Product.image if empty, rest become ProductPhoto rows. Only image
    extensions in ALLOWED_EXTS accepted; each is verified with Pillow.
    Ignores __MACOSX and hidden files.

    Returns dict with:
        matched   – list of (Product, int) tuples
        unmatched – list of folder name strings
        errors    – list of error message strings
        skipped   – list of {"name": str, "reason": str} dicts
    """
    from PIL import Image as PilImage
    from django.core.files.uploadedfile import SimpleUploadedFile
    from store.uploads import validate_zip_safety

    matched = []
    unmatched = []
    errors = []
    skipped = []

    by_name, by_sku, by_slug = _build_lookup()

    # Validate the ZIP for safety before processing
    try:
        zip_file_obj = SimpleUploadedFile("upload.zip", zip_bytes, content_type="application/zip")
        validate_zip_safety(zip_file_obj)
    except Exception as exc:
        errors.append(str(exc))
        return {"matched": matched, "unmatched": unmatched, "errors": errors, "skipped": skipped}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Discover unique top-level folder names
            folders = set()
            for item in zf.namelist():
                parts = item.rstrip("/").split("/")
                folder = parts[0]
                if (
                    len(parts) >= 2
                    and folder
                    and not folder.startswith("__MACOSX")
                    and not folder.startswith(".")
                ):
                    folders.add(folder)

            for folder in sorted(folders):
                product = _match_product(folder, by_name, by_sku, by_slug)
                if product is None:
                    unmatched.append(folder)
                    continue

                # Collect direct image children, sorted by filename
                images = []
                for item in sorted(zf.namelist()):
                    parts = item.split("/")
                    if len(parts) != 2 or parts[0] != folder:
                        continue
                    filename = parts[1]
                    if not filename or filename.startswith("."):
                        continue
                    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
                    if ext in _VIDEO_EXTS:
                        skipped.append({"name": filename, "reason": "Videos not attached to products in bulk upload"})
                        continue
                    if ext not in ALLOWED_EXTS:
                        skipped.append({"name": filename, "reason": "blocked file type"})
                        continue
                    images.append((filename, item))

                if not images:
                    unmatched.append(folder)
                    continue

                if replace:
                    product.photos.all().delete()
                    if product.image:
                        product.image.delete(save=False)
                        product.image = None
                        product.save(update_fields=["image"])

                count = 0
                for idx, (filename, zip_path) in enumerate(images):
                    data = zf.read(zip_path)
                    try:
                        img_obj = PilImage.open(io.BytesIO(data))
                        img_obj.verify()
                    except Exception:
                        skipped.append({"name": filename, "reason": "invalid image data"})
                        continue

                    cf = ContentFile(data, name=filename)
                    if idx == 0 and not product.image:
                        product.image.save(filename, cf, save=True)
                    else:
                        order = product.photos.count()
                        ProductPhoto.objects.create(
                            product=product, image=cf, order=order
                        )
                    count += 1

                if count:
                    matched.append((product, count))
                else:
                    unmatched.append(folder)

    except zipfile.BadZipFile:
        errors.append("The uploaded file is not a valid ZIP archive.")
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")

    return {"matched": matched, "unmatched": unmatched, "errors": errors, "skipped": skipped}
