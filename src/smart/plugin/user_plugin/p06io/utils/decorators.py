from functools import wraps


#######################
# add_method_to_class #
#######################

def add_method_to_class(cls):
    '''
    Adds a function as a method to a class.

    Parameters
    ----------
    cls : object
        The class to add the method to.
    '''

    def decorator(func):
        '''
        The decorator
        '''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            '''
            The wrapper
            '''

            return func(self, *args, **kwargs)
        setattr(cls, func.__name__, wrapper)
        return func
    return decorator
