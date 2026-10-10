"""Small helpers for templates: rupee formatting, toy drawings and icons."""
import itertools
import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

INK = "#2E2A5C"
S = f'stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'

# Sticker-style toy drawings on a 120×120 grid. Used until a real photo is uploaded.
ILLUSTRATIONS = {
    "rings": f'''
      <rect x="56" y="14" width="8" height="82" rx="4" fill="#fff" {S}/>
      <ellipse cx="60" cy="96" rx="40" ry="10" fill="#FFC83D" {S}/>
      <ellipse cx="60" cy="84" rx="34" ry="11" fill="#FF9B73" {S}/>
      <ellipse cx="60" cy="68" rx="27" ry="10" fill="#78AEFF" {S}/>
      <ellipse cx="60" cy="53" rx="21" ry="9" fill="#4FD1A0" {S}/>
      <ellipse cx="60" cy="39" rx="15" ry="7" fill="#FF86AE" {S}/>
      <circle cx="60" cy="22" r="9" fill="#B394FF" {S}/>''',
    "blocks": f'''
      <rect x="18" y="62" width="40" height="40" rx="8" fill="#FF9B73" {S}/>
      <rect x="62" y="62" width="40" height="40" rx="8" fill="#78AEFF" {S}/>
      <rect x="40" y="18" width="40" height="40" rx="8" fill="#FFC83D" {S} transform="rotate(-6 60 38)"/>
      <path d="M30 82h16M38 74v16" {S} fill="none"/>
      <circle cx="82" cy="82" r="9" fill="#fff" {S}/>
      <path d="M52 44l8-14 8 14z" fill="#fff" {S} transform="rotate(-6 60 38)"/>''',
    "cards": f'''
      <rect x="22" y="30" width="56" height="72" rx="9" fill="#fff" {S} transform="rotate(-10 50 66)"/>
      <rect x="42" y="20" width="56" height="72" rx="9" fill="#fff" {S} transform="rotate(6 70 56)"/>
      <circle cx="70" cy="46" r="12" fill="#FFC83D" {S}/>
      <path d="M58 76h26M62 84h18" {S} fill="none"/>
      <path d="M64 46h0M76 46h0" {S} fill="none"/>
      <path d="M65 51q5 4 10 0" {S} fill="none"/>''',
    "balls": f'''
      <circle cx="42" cy="72" r="26" fill="#4FD1A0" {S}/>
      <circle cx="82" cy="78" r="20" fill="#FF86AE" {S}/>
      <circle cx="70" cy="36" r="16" fill="#78AEFF" {S}/>
      <g fill="{INK}"><circle cx="32" cy="64" r="3"/><circle cx="44" cy="60" r="3"/><circle cx="52" cy="72" r="3"/>
      <circle cx="38" cy="78" r="3"/><circle cx="46" cy="88" r="3"/><circle cx="76" cy="72" r="2.6"/>
      <circle cx="88" cy="76" r="2.6"/><circle cx="80" cy="86" r="2.6"/><circle cx="66" cy="32" r="2.4"/>
      <circle cx="74" cy="40" r="2.4"/></g>''',
    "board": f'''
      <path d="M14 78 Q60 40 106 78" fill="#FFC83D" {S}/>
      <path d="M14 78 Q60 52 106 78" fill="#FF9B73" {S}/>
      <path d="M30 90h60" {S} fill="none"/>
      <circle cx="60" cy="30" r="9" fill="#B394FF" {S}/>
      <path d="M60 39v18M48 46l12 4 12-4M60 57l-8 10M60 57l8 10" {S} fill="none"/>''',
    "puzzle": f'''
      <path d="M20 22h34v10a8 8 0 1 0 16 0V22h30v34H90a8 8 0 1 0 0 16h10v28H66V90a8 8 0 1 0-16 0v10H20V72h10a8 8 0 1 0 0-16H20z"
            fill="#78AEFF" {S}/>
      <path d="M58 22v34M20 60h80" stroke="{INK}" stroke-width="2" stroke-dasharray="4 5" fill="none"/>''',
    "beads": f'''
      <path d="M16 30 C40 30 30 90 60 90 S90 40 104 40" stroke="{INK}" stroke-width="2.5" fill="none"/>
      <circle cx="24" cy="31" r="9" fill="#FF9B73" {S}/>
      <rect x="31" y="44" width="16" height="16" rx="4" fill="#4FD1A0" {S}/>
      <circle cx="46" cy="78" r="9" fill="#FFC83D" {S}/>
      <path d="M58 82l9 0 0 14-9 0z" fill="#B394FF" {S}/>
      <circle cx="80" cy="68" r="9" fill="#FF86AE" {S}/>
      <rect x="88" y="34" width="16" height="16" rx="8" fill="#78AEFF" {S}/>
      <rect x="96" y="30" width="16" height="10" rx="3" fill="{INK}"/>''',
    "tunnel": f'''
      <path d="M16 84 L36 40 H104 L84 84 Z" fill="#B394FF" {S}/>
      <ellipse cx="26" cy="62" rx="12" ry="24" fill="#fff" {S}/>
      <path d="M48 40l-20 44M64 40l-20 44M80 40l-20 44M96 40l-20 44" stroke="{INK}" stroke-width="2" fill="none"/>
      <path d="M12 96h96" {S} fill="none"/>''',
    "dough": f'''
      <rect x="18" y="58" width="36" height="40" rx="6" fill="#FF86AE" {S}/>
      <rect x="14" y="50" width="44" height="12" rx="5" fill="#fff" {S}/>
      <rect x="62" y="62" width="36" height="36" rx="6" fill="#4FD1A0" {S}/>
      <path d="M62 62 q18 -26 36 0" fill="#FFC83D" {S}/>
      <path d="M30 74h12M30 84h8" {S} fill="none"/>''',
    "shapes": f'''
      <rect x="16" y="56" width="88" height="44" rx="10" fill="#FFC83D" {S}/>
      <circle cx="38" cy="78" r="9" fill="#fff" {S}/>
      <rect x="54" y="69" width="18" height="18" rx="3" fill="#fff" {S}/>
      <path d="M80 87l9-17 9 17z" fill="#fff" {S}/>
      <circle cx="40" cy="30" r="12" fill="#FF86AE" {S}/>
      <rect x="66" y="16" width="24" height="24" rx="4" fill="#4FD1A0" {S} transform="rotate(12 78 28)"/>''',
}

ICONS = {
    "cart": '<path d="M3 4h2.5l2.2 10.2a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.5L21 8H6.3"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "truck": '<path d="M2 6h11v10H2zM13 10h4.5l3.5 3.5V16h-8"/><circle cx="6" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    "cash": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><circle cx="12" cy="12" r="2.6"/><path d="M6 9.5v5M18 9.5v5"/>',
    "heart": '<path d="M12 20s-7-4.4-8.6-9A4.6 4.6 0 0 1 12 6.6 4.6 4.6 0 0 1 20.6 11C19 15.6 12 20 12 20z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "return": '<path d="M9 7L4 12l5 5"/><path d="M4 12h11a5 5 0 0 1 0 10h-2"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "star": '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/>',
    "home": '<path d="M3.5 11L12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5h4v5"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
    "tag": '<path d="M3.5 12.5V4h8.5l8.5 8.5-8.5 8.5z"/><circle cx="8" cy="8.5" r="1.4"/>',
    "chev-l": '<path d="M15 5l-7 7 7 7"/>',
    "chev-r": '<path d="M9 5l7 7-7 7"/>',
    "chev-d": '<path d="M6 9l6 6 6-6"/>',
    "arrow-r": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "shield": '<path d="M12 3l7.5 3v5.5c0 4.5-3.2 8.2-7.5 9.5-4.3-1.3-7.5-5-7.5-9.5V6z"/><path d="M8.8 12l2.2 2.2 4.3-4.4"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "pin": '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>',
    "box": '<path d="M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5z"/><path d="M3.5 7.5L12 12l8.5-4.5M12 12v9"/>',
}

WHATSAPP = ('<svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.4.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.9 11.9 0 0 0 4.5 4c1.7.7 2.4.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.4-.3z"/></svg>')


def _mix(hex_color, target, amount):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    t = 255 if target == "light" else 0
    r, g, b = (round(c + (t - c) * amount) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


_TAG = re.compile(r"<(\w+)([^<>]*?)(/?)>")
_counter = itertools.count()


def _clay(body):
    """Turn the flat outlined drawing into soft 3D 'clay' shapes:
    gradient fills, a darker edge of the same colour, ink only for small details."""
    uid = f"cl{next(_counter)}"
    colors = {}

    def fix(m):
        tag, attrs, close = m.groups()
        fill = re.search(r'fill="(#[0-9A-Fa-f]{6}|#fff)"', attrs)
        if not fill or fill.group(1).upper() == INK.upper():
            if 'fill="none"' in attrs:  # detail lines (faces, dashes) stay ink, a bit thinner
                attrs = attrs.replace('stroke-width="3"', 'stroke-width="2.6"')
            return f"<{tag}{attrs}{close}>"
        base = fill.group(1).upper()
        base = "#FFFFFF" if base == "#FFF" else base
        if base == "#FFFFFF":
            base = "#F4F1FF"
        gid = f"{uid}-{base[1:]}"
        colors[gid] = base
        attrs = attrs.replace(fill.group(0), f'fill="url(#{gid})"')
        attrs = re.sub(r'stroke="[^"]+"', f'stroke="{_mix(base, "dark", .32)}"', attrs)
        attrs = attrs.replace('stroke-width="3"', 'stroke-width="1.6"')
        return f"<{tag}{attrs}{close}>"

    body = _TAG.sub(fix, body)
    defs = "".join(
        f'<radialGradient id="{gid}" cx="32%" cy="26%" r="80%">'
        f'<stop offset="0" stop-color="{_mix(c, "light", .6)}"/>'
        f'<stop offset=".55" stop-color="{c}"/>'
        f'<stop offset="1" stop-color="{_mix(c, "dark", .2)}"/></radialGradient>'
        for gid, c in colors.items()
    )
    shadow = (f'<filter id="{uid}-blur" x="-20%" y="-50%" width="140%" height="200%">'
              f'<feGaussianBlur stdDeviation="3"/></filter>')
    ground = f'<ellipse cx="60" cy="108" rx="40" ry="6" fill="{INK}" opacity=".16" filter="url(#{uid}-blur)"/>'
    return f"<defs>{defs}{shadow}</defs>{ground}{body}"


@register.simple_tag
def illus(name, label=""):
    body = _clay(ILLUSTRATIONS.get(name, ILLUSTRATIONS["blocks"]))
    aria = f'role="img" aria-label="{escape(label)}"' if label else 'aria-hidden="true"'
    return mark_safe(f'<svg class="illus" viewBox="0 0 120 120" {aria}>{body}</svg>')


@register.simple_tag
def icon(name, size=20, stroke=2):
    body = ICONS.get(name, "")
    return mark_safe(
        f'<svg width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )


@register.simple_tag
def whatsapp_icon(size=28, color="#fff"):
    svg = WHATSAPP.replace('width="28" height="28"', f'width="{int(size)}" height="{int(size)}"')
    return mark_safe(svg.replace('fill="#fff"', f'fill="{escape(color)}"'))


@register.simple_tag
def stars(n):
    star = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="{f}" aria-hidden="true">'
            '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/></svg>')
    n = int(n or 0)
    return mark_safe("".join(star.format(f="currentColor" if i < n else "#E4E0F2") for i in range(5))
                     + f'<span class="sr-only">{n} out of 5 stars</span>')


@register.filter
def rs(value):
    """12500 -> 'Rs 12,500'"""
    try:
        return f"Rs {int(value):,}"
    except (TypeError, ValueError):
        return value


@register.simple_tag
def logo(size=40):
    # Mint block with a jumping child — the LittleMove mark.
    # Jumping child inside a rounded block — matches the LittleMove logo idea.
    s = int(size)
    return mark_safe(f'''<svg width="{s}" height="{s}" viewBox="0 0 48 48" aria-hidden="true">
      <rect x="2" y="2" width="44" height="44" rx="14" fill="#BDEBD8" stroke="{INK}" stroke-width="3"/>
      <circle cx="24" cy="13.5" r="4.6" fill="#FFD966" stroke="{INK}" stroke-width="2.6"/>
      <path d="M13 17l11 6 11-6M24 23v7M24 30l-7 7M24 30l7 7" fill="none" stroke="{INK}" stroke-width="3"
            stroke-linecap="round" stroke-linejoin="round"/></svg>''')


@register.filter
def first_name(value):
    parts = str(value or "").split()
    return parts[0] if parts else ""


