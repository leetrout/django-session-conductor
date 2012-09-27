from functools import wraps


class SessionConductor(object):
    """Class that is used as a decorator when instantiated to make working
    with sessions easier.
    
    Provides helpers to reset a session, destroy specific session vars,
    save specific vars, or even skip vars (temporarily remove during the
    execution of a view).
    """
    def __init__(self, save=None, destroy=None, skip=None, ensure=None):
        for k, v in locals().items():
            attr = '_%s' % k
            if k == 'ensure':
                v = v or {}
            else:
                v = v or []
            setattr(self, attr, v)
    
    def save(self, xtra=None):
        """Declare keys to be saved.
        
        Destroy keys override this setting.
        """
        return self._save + (xtra or [])
    
    def destroy(self, xtra):
        """Explicitly declare keys to be destroyed.
        
        If destroy keys are present ONLY those keys are removed.
        
        For instance, if a session has 3 keys 'foo', 'bar', 'baz' and the
        default conductor decorates the view they will all be deleted before
        the view is executed.
        
        However, using @sessionconductor(destroy=('foo',)) will only delete
        foo.
        """
        return self._destroy + (xtra or [])
    
    def skip(self, xtra):
        """Session keys to be removed before this view executes.
        
        They will be reinstated after the view is executed.
        """
        return self._skip + (xtra or [])
    
    def ensure(self, xtra):
        """Dictionary of session keys that should be present and a callable
        to execute as the key's value.
        
        If value is not a callable self.handle_missing_key will be called and
        the value will be passed as the first argument.
        """
        ens = self._ensure.copy()
        ens.update(xtra or {})
        return ens
    
    def reset(self, session, keeps):
        """Reset a session (delete unneeded keys).
        
        Removes any keys that are not in `keeps` or do not start with an
        underscore.
        """
        for x in session.keys():
            if not x.startswith('_') and x not in keeps:
                del session[x]
    
    def handle_missing_key(self, key, value=None):
        """Called when a required key is missing from the session.
        
        Raises an exception by default.
        """
        exc = 'Session is missing key (%s)' % key
        raise Exception(exc)
    
    def skipped_removed(self, session):
        """Called when the skipped keys have been removed from the session."""
        pass
    
    def skipped_pre_restore(self, session):
        """Called after the wrapped function has executed but before the
        skipped keys have been reinstated.
        """
        pass
    
    def get_decorator(self, *args, **kwargs):
        """Returns the session conductor decorator."""
        save = self.save(list(args))
        destroy = self.destroy(kwargs.get('destroy', []))
        skip = self.skip(kwargs.get('skip', []))
        ensured = kwargs.get('ensure', {})
        ensure = self.ensure(ensured).keys()
        keeps = save + skip + ensure
        
        def dec(fn):
            @wraps(fn)
            def wrapper(request, *args, **kwargs):
                sess = request.session
                # always ensure keys
                for x in ensure:
                    if x not in sess:
                        self.handle_missing_key(x, ensured[x])
                
                # destroy or reset
                if destroy:
                    for x in destroy:
                        del sess[x]
                else:
                    self.reset(sess, keeps)
                
                # remove skipped
                to_restore = {x: request.session.get(x) for x in skip}
                for x in to_restore:
                    del sess[x]
                
                # execute
                ret = fn(request, *args, **kwargs)
                
                # reinstitute skipped
                for x in to_restore:
                    sess[x] = to_restore[x]
                return ret
            return wrapper
        return dec
    
    def __call__(self, *args, **kwargs):
        """Shortcut to get the decorator.
        
        Allows usage like:
        sc = SessionConductor()
        
        @sc()
        def foo():
        ...
        """
        return self.get_decorator(*args, **kwargs)
    
    decorator = property(get_decorator)
