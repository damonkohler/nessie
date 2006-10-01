
class curry:
    """curry -- associating parameters with a function
    @author: Scott David Daniels

    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52549

    In functional programming, currying is a way to bind arguments
    with a function and wait for the rest of the arguments to show up
    later. You 'curry' in the first few parameters to a function,
    giving you a function that takes subsequent parameters as input
    and calls the original with all of those parameters. This recipe
    uses a class instance to hold the parameters before their first
    use.

    For example:
    double = curry(operator.mul, 2)
    triple = curry(operator.mul, 3)

    """    
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs
        return self.fun(*(self.pending + args), **kw)
