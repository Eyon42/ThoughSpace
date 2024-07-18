import io
import base64

from xml.sax import saxutils

from PIL import Image
from PIL import ImageFont
from wordcloud import *


class ThoughtCloud(WordCloud):
  def __init__(self, font_path=None, width=400, height=200, margin=2, ranks_only=None, prefer_horizontal=0.9, mask=None, scale=1, color_func=None, max_words=200, min_font_size=4, stopwords=None, random_state=None, background_color='black', max_font_size=None, font_step=1, mode="RGB", relative_scaling='auto', regexp=None, collocations=True, colormap=None, normalize_plurals=True, contour_width=0, contour_color='black', repeat=False, include_numbers=False, min_word_length=0, collocation_threshold=30):
    super().__init__(font_path, width, height, margin, ranks_only, prefer_horizontal, mask, scale, color_func, max_words, min_font_size, stopwords, random_state, background_color, max_font_size, font_step, mode, relative_scaling, regexp, collocations, colormap, normalize_plurals, contour_width, contour_color, repeat, include_numbers, min_word_length, collocation_threshold)
    # with open(self.font_path, "rb") as f:
    #   self.font_file = io.BytesIO(f.read())

  def to_svg(self, embed_font=False, optimize_embedded_font=True, embed_image=False):
    """Export to SVG.

    Font is assumed to be available to the SVG reader. Otherwise, text
    coordinates may produce artifacts when rendered with replacement font.
    It is also possible to include a subset of the original font in WOFF
    format using ``embed_font`` (requires `fontTools`).

    Note that some renderers do not handle glyphs the same way, and may
    differ from ``to_image`` result. In particular, Complex Text Layout may
    not be supported. In this typesetting, the shape or positioning of a
    grapheme depends on its relation to other graphemes.

    Pillow, since version 4.2.0, supports CTL using ``libraqm``. However,
    due to dependencies, this feature is not always enabled. Hence, the
    same rendering differences may appear in ``to_image``. As this
    rasterized output is used to compute the layout, this also affects the
    layout generation. Use ``PIL.features.check`` to test availability of
    ``raqm``.

    Consistant rendering is therefore expected if both Pillow and the SVG
    renderer have the same support of CTL.

    Contour drawing is not supported.

    Parameters
    ----------
    embed_font : bool, default=False
      Whether to include font inside resulting SVG file.

    optimize_embedded_font : bool, default=True
      Whether to be aggressive when embedding a font, to reduce size. In
      particular, hinting tables are dropped, which may introduce slight
      changes to character shapes (w.r.t. `to_image` baseline).

    embed_image : bool, default=False
      Whether to include rasterized image inside resulting SVG file.
      Useful for debugging.

    Returns
    -------
    content : string
      Word cloud image as SVG string
    """

    # TODO should add option to specify URL for font (i.e. WOFF file)

    # Make sure layout is generated
    self._check_generated()

    # Get output size, in pixels
    if self.mask is not None:
      width = self.mask.shape[1]
      height = self.mask.shape[0]
    else:
      height, width = self.height, self.width

    # Get max font size
    if self.max_font_size is None:
      max_font_size = max(w[1] for w in self.layout_)
    else:
      max_font_size = self.max_font_size

    # Text buffer
    result = []

    # Get font information
    font = ImageFont.truetype(self.font_path, int(max_font_size * self.scale))
    raw_font_family, raw_font_style = font.getname()
    # TODO properly escape/quote this name?
    font_family = repr(raw_font_family)
    # TODO better support for uncommon font styles/weights?
    raw_font_style = raw_font_style.lower()
    if 'bold' in raw_font_style:
      font_weight = 'bold'
    else:
      font_weight = 'normal'
    if 'italic' in raw_font_style:
      font_style = 'italic'
    elif 'oblique' in raw_font_style:
      font_style = 'oblique'
    else:
      font_style = 'normal'

    # Add header
    result.append(
      '<svg'
      ' xmlns="http://www.w3.org/2000/svg"'
      ' width="{}"'
      ' height="{}"'
      '>'
      .format(
        width * self.scale,
        height * self.scale
      )
    )

    # Embed font, if requested
    if embed_font:

      # Import here, to avoid hard dependency on fonttools
      import fontTools
      import fontTools.subset

      # Subset options
      options = fontTools.subset.Options(

        # Small impact on character shapes, but reduce size a lot
        hinting=not optimize_embedded_font,

        # On small subsets, can improve size
        desubroutinize=optimize_embedded_font,

        # Try to be lenient
        ignore_missing_glyphs=True,
      )

      # Load and subset font
      ttf = fontTools.subset.load_font(self.font_path, options)
      subsetter = fontTools.subset.Subsetter(options)
      characters = {c for item in self.layout_ for c in item[0][0]}
      text = ''.join(characters)
      subsetter.populate(text=text)
      subsetter.subset(ttf)

      # Export as WOFF
      # TODO is there a better method, i.e. directly export to WOFF?
      buffer = io.BytesIO()
      ttf.saveXML(buffer)
      buffer.seek(0)
      woff = fontTools.ttLib.TTFont(flavor='woff')
      woff.importXML(buffer)

      # Create stylesheet with embedded font face
      buffer = io.BytesIO()
      woff.save(buffer)
      data = base64.b64encode(buffer.getbuffer()).decode('ascii')
      url = 'data:application/font-woff;charset=utf-8;base64,' + data
      result.append(
        '<style>'
        '@font-face{{'
        'font-family:{};'
        'font-weight:{};'
        'font-style:{};'
        'src:url("{}")format("woff");'
        '}}'
        '</style>'
        .format(
          font_family,
          font_weight,
          font_style,
          url
        )
      )

    # Select global style
    result.append(
      '<style>'
      'text{{'
      'font-family:{};'
      'font-weight:{};'
      'font-style:{};'
      '}}'
      '</style>'
      .format(
        font_family,
        font_weight,
        font_style
      )
    )

    # Add background
    if self.background_color is not None:
      result.append(
        '<rect'
        ' width="100%"'
        ' height="100%"'
        ' style="fill:{}"'
        '>'
        '</rect>'
        .format(self.background_color)
      )

    # Embed image, useful for debug purpose
    if embed_image:
      image = self.to_image()
      data = io.BytesIO()
      image.save(data, format='JPEG')
      data = base64.b64encode(data.getbuffer()).decode('ascii')
      result.append(
        '<image'
        ' width="100%"'
        ' height="100%"'
        ' href="data:image/jpg;base64,{}"'
        '/>'
        .format(data)
      )

    # For each word in layout
    for (word, count), font_size, (y, x), orientation, color in self.layout_:
      x *= self.scale
      y *= self.scale

      # Get text metrics
      font = ImageFont.truetype(self.font_path, int(font_size * self.scale))
      (size_x, size_y), (offset_x, offset_y) = font.font.getsize(word)
      ascent, descent = font.getmetrics()

      # Compute text bounding box
      min_x = -offset_x
      max_x = size_x - offset_x
      max_y = ascent - offset_y

      # Compute text attributes
      attributes = {}
      if orientation == Image.ROTATE_90:
        x += max_y
        y += max_x - min_x
        transform = 'translate({},{}) rotate(-90)'.format(x, y)
      else:
        x += min_x
        y += max_y
        transform = 'translate({},{})'.format(x, y)

      # Create node
      attributes = ' '.join('{}="{}"'.format(k, v) for k, v in attributes.items())
      result.append(
        '<text'
        ' transform="{}"'
        ' font-size="{}"'
        ' fill="rgb{}"'
        ' stroke="rgb{}"'
        '>'
        '{}'
        '</text>'
        .format(
          transform,
          font_size * self.scale,
          color,
          color,
          saxutils.escape(word)
        )
      )

    # TODO draw contour

    # Complete SVG file
    result.append('</svg>')
    return '\n'.join(result)