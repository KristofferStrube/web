import math
import shlex
from collections import Counter


class Option:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.key = None
        self.name = kwargs.pop('name', None)
        self._sheet_count = kwargs.pop('sheets', None)
        if kwargs:
            raise TypeError(kwargs.keys())

    def sheet_count(self, n):
        if self._sheet_count is None:
            return n
        else:
            return self._sheet_count(n)

    def lp_options(self):
        return [o for arg in self.args for o in
                ((arg,) if isinstance(arg, str) else arg.lp_options())]

    def lp_string(self):
        return ' '.join('-o %s' % shlex.quote(s) for s in self.lp_options())

    def __str__(self):
        return self.name or self.key or self.lp_string()

    def __repr__(self):
        return '<Option %s>' % self.key if self.key else '<Option>'


def set_option_keys(cls):
    for k in dir(cls):
        v = getattr(cls, k)
        if isinstance(v, Option):
            v.key = k
    return cls


@set_option_keys
class Options:
    '''
    >>> Options.booklet.lp_string()
    '-o Booklet=Left'
    >>> Options.parse(Options.booklet.lp_string())
    [<Option booklet>]
    >>> Options.parse(Options.stapled_a5_book.lp_string())
    [<Option stapled_a5_book>]
    >>> all([o] == Options.parse(o.lp_string()) for o in Options.get_options())
    True
    '''

    # Print pages 1,2,3,1,2,3,1,2,3,... instead of 1,1,1,...,2,2,2...
    collate = Option('Collate=True')

    # Printing an A4 document with just Booklet=Left and no
    # PageSize/fit-to-page will result in a folded booklet made from A3 paper.
    booklet = Option('Booklet=Left')

    # SaddleStitch probably only makes sense with Booklet.
    # SaddleStitch means fold and staple.
    stapled_folded_book = Option(booklet, 'SaddleStitch=On')

    # The following options force the source material to A5 size
    # so that the booklet option will use A4 paper.
    a5paper = Option('PageSize=A5')
    fit_to_page = Option('fit-to-page')
    fit_a5 = Option(a5paper, fit_to_page)

    a4paper = Option("PageSize=A4")
    fit_a4 = Option(a4paper, fit_to_page)

    # Possible interpretation of 1PLU = one punch left up
    staple_top_left = Option("Staple=1PLU")

    # Possible interpretation of 2PL = two punches left
    staple_left = Option("Staple=2PL")

    a5_book = Option(booklet, fit_a5,
                     name='A5-hæfte',
                     sheets=lambda n: math.ceil(n / 4))

    stapled_a5_book = Option(stapled_folded_book, fit_a5,
                             name='A5-hæfte, klipset+foldet',
                             sheets=lambda n: math.ceil(n / 4))

    twosided_base = Option('Duplex=DuplexNoTumble',
                           sheets=lambda n: math.ceil(n / 2))
    twosided = Option(collate, twosided_base, name='Tosidet',
                      sheets=lambda n: math.ceil(n / 2))
    onesided_base = Option('Duplex=None')
    onesided = Option(collate, onesided_base, name='Enkeltsidet')

    a4_book = Option(a4paper, fit_a4, twosided)

    a4_book_single = Option(
        a4_book,
        staple_top_left,
        name="A4-bog, én klips",
        sheets=lambda n: math.ceil(n / 2),
    )
    a4_book_double = Option(
        a4_book, staple_left, name="A4-bog, to klips", sheets=lambda n: math.ceil(n / 2)
    )

    @classmethod
    def get_options(cls):
        values = [getattr(cls, k) for k in sorted(dir(cls))]
        options = [v for v in values if isinstance(v, Option)]
        return options

    @classmethod
    def parse(cls, string):
        # shlex.split might raise ValueError
        args = shlex.split(string)

        # 'string' was a valid command line option string,
        # now let's check if it is on the form (-o <OPTION>)*
        invalid = [o for o in args[::2] if o != '-o']
        if invalid:
            raise ValueError('Every other argument should be "-o": %s' %
                             (invalid,))
        if len(args) % 2 != 0:
            raise ValueError('Last option not supplied')

        # Throw away all the -o's
        input_options = args[1::2]

        remaining = Counter(input_options)
        result = []

        all_options = cls.get_options()
        # Start with 'largest' options to avoid problems with one option being
        # a subset of another option. That is, if we have (in class Options)
        #     foo = Option('x')
        #     bar = Option('y')
        #     baz = Option(foo, bar)
        # and the input is baz.lp_string() (which is '-o x -o y'),
        # we must consider baz before foo or bar to ensure that
        # parse('-o x -o y') == [Options.baz].
        all_options.sort(key=lambda o: (len(o.lp_options()), o.lp_options()))
        for o in reversed(all_options):
            # Invariant: result + remaining == input_options
            result_lp_options = (Counter(r.lp_options()) for r in result)
            assert sum(result_lp_options, remaining) == Counter(input_options)

            o_c = Counter(o.lp_options())
            if (remaining - o_c) + o_c == remaining:
                # o_c contained in remaining
                remaining -= o_c
                result.append(o)

        # In the future we might want to put the unparsed options into a
        # CustomOption type (or similar).
        if remaining:
            raise ValueError("Unrecognized: %s" %
                             ' '.join(remaining.elements()))
        return result


# These are the choices from which the user must select exactly one.
# The first choice is the default choice.
choices = [getattr(Options, k) for k in '''
    twosided onesided
'''.split()]
# a5_book and stapled_a5_book removed since the new Xerox Altalink C8055
# printer at MATH does not support booklet printing on Linux :-(
