def f_google(a, b: str):
    """A google style docstring.

    Args:
        a (int): The a parameter.
        b: The b parameter.

    Custom Admonition:
        Some text.
    """


def f_sphinx(a, b: str):
    """A sphinx style docstring.

    :param a: The a parameter.
    :type a: int
    :param b: The b parameter.
    """


def f_numpy(a, b: str):
    """A numpy style docstring.

    Parameters
    ----------
    a: int
        The a parameter.
    b:
        The b parameter.

    Custom Admonition
    -----------------
    Some text.
    """


# we set an option by default in griffe's numpy parsing
# to allow linebreaks in parameter tables
def f_numpy_with_linebreaks(a, b: str):
    """A numpy style docstring.

    Parameters
    ----------
    a: int
        The a parameter.

    b:
        The b parameter.
    """


def f_numpy_markdown_list(data, options: dict):
    """A function with markdown list in parameter description.

    Parameters
    ----------
    data: str
        The data parameter with markdown list:

        - First item
        - Second item
        - Third item
    options:
        Configuration options with list:

        - `option1`: First option
        - `option2`: Second option
    """


def f_numpy_single_newline(text: str):
    """A function with single newlines in description.

    Parameters
    ----------
    text: str
        This is a long description that spans
        multiple lines but uses single newlines.
        It should be collapsed into a single line.
    """


def f_google_kwargs(a, b=1, *args, **kwargs):
    """A google style docstring documenting parameters taken by **kwargs.

    Args:
        a (int): A required parameter.
        b (int): A parameter with a default.
        args (list): Extra positional arguments.
        c (int): A parameter taken by **kwargs.
        kwargs (dict): Other keywords.
    """
