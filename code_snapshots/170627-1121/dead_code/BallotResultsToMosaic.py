import Image, ImageFont, ImageDraw
#get font size
_sszx, _sszy = ImageFont.load_default().getsize(14*'M')
#inset size, px
_xins, _yins = 10, 5
def results_to_mosaic(results):
    """Return an image that is a mosaic of all ovals
    from a list of Votedata"""
    # Each tile in the mosaic:
    #  _______________________
    # |           ^           |
    # |         _yins         |
    # |           v           |
    # |        _______        |
    # | _xins | image | _xins |
    # |<----->|_______|<----->| vop or wrin
    # |           ^           |
    # |         _yins         |
    # |           v           |
    # |        _______        |
    # | _xins | _ssz  | _xins |
    # |<----->|_______|<----->| label
    # |           ^           |
    # |         _yins         |
    # |           v           |
    # |_______________________|
    #
    # We don't know for sure whether the label or the image is longer so we
    # take the max of the two.
    vops, wrins = [], []
    vopx, vopy = 0, 0
    for r in results:
        if r.is_writein:
            wrins.append(r)
        else:
            #grab first nonnil image to get vop size
            if vopx == 0 and r.image is not None:
                vopx, vopy = r.image.size
            vops.append(r)

    wrinx, wriny = 0, 0
    if wrins:
        wrinx, wriny = wrins[0].image.size

    # compute area of a vop + decorations
    xs = max(vopx, _sszx) + 2*_xins
    ys = vopy + _sszy + 3*_yins
    # compute area of a wrin + decorations
    wxs = max(wrinx, _sszx) + 2*_xins
    wys = wriny + _sszy + 3*_yins
    if wrinx == 0:
        wxs, wxs = 0, 0 #no wrins

    #compute dimensions of mosaic
    xl = max(10*xs, 4*wxs)
    yle = ys*(1 + len(vops)/10) #end of vop tiling
    yl =  yle + wys*(1 + len(wrins)/4)
    yle += _yins - 1 #so we don't have to add this each time

    moz = Image.new("RGB", (xl, yl), color="white")
    draw = ImageDraw.Draw(moz)
    text = lambda x, y, s: draw.text((x, y), s, fill="black")
    #tile vops
    for i, vop in enumerate(vops):
        d, m = divmod(i, 10)
        x = m*xs + _xins
        y = d*ys + _yins
        if vop.image is not None:
            moz.paste(vop.image, (x, y))
        else:
            X = x + _xins
            Y = y + _yins
            draw.line((X, Y, X + vopx, Y + vopy), fill="red")
            draw.line((X, Y + vopy, X + vopx, Y), fill="red")
        y += _yins + vopy
        label = "%s:%04dx%04d%s%s%s" % (
            vop.number,
            vop.coords[0],
            vop.coords[1],
            "-" if vop.was_voted or vop.ambiguous else "",
            "!" if vop.was_voted else "",
            "?" if vop.ambiguous else ""
        )
        text(x, y, label)

    #tile write ins
    for i, wrin in enumerate(wrins): #XXX this part is screwed up and I need to fix it
        d, m = divmod(i, 4)
        x = m*wxs + _xins
        y = d*wys + yle
        moz.paste(wrin.image, (x, y))
        y += _yins + wriny
        label = "%s_%04d_%04d" % (wrin.number, wrin.coords[0], wrin.coords[1])
        text(x, y, label)

    return moz

