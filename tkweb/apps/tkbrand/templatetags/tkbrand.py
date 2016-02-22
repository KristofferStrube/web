from django import template
from django.utils.safestring import mark_safe
from tkweb.apps.tkbrand import util

register = template.Library()

html_tk = ('<span '
           'style="vertical-align: -0.4pt">T</span><span '
           'style="font-weight: bold">&Aring;</span>G<span '
           'style="display: inline-block; transform: rotate(8deg); '
           '-webkit-transform: rotate(8deg)">E</span><span '
           'style="vertical-align: -0.6pt">K</span><span '
           'style="vertical-align: 0.2pt; font-weight: bold">A</span><span '
           'style="vertical-align: -0.6pt">M</span><span '
           'style="display: inline-block; transform: rotate(-8deg); '
           '-webkit-transform: rotate(-8deg); font-weight: bold">M</span>ER')

html_tket = html_tk + '<span style="vertical-align: 0.6pt">ET</span>'


@register.simple_tag
def tk(monospace=None):
    return mark_safe('<span class="tk-brand">' + html_tk + '</span>')


@register.simple_tag
def tket():
    return mark_safe('<span class="tk-brand">' + html_tket + '</span>')

@register.filter
def gfyearPP(gfyear):
    return util.gfyearPP(gfyear)

@register.filter
def gfyearPPslash(gfyear):
    return util.gfyearPPslash(gfyear)