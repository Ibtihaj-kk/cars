#!/usr/bin/env python
"""
Django startup patch for template context bug
Apply this patch to fix Django's BaseContext.__copy__ method
"""

def patch_django_template_context():
    """
    Patch Django's BaseContext.__copy__ method to fix the bug where
    copy(super()) fails because super() doesn't have __dict__
    
    Also patch RequestContext.new to fix missing _processors_index
    """
    try:
        from django.template.context import BaseContext, RequestContext
        import copy
        
        # --- Patch 1: BaseContext.__copy__ ---
        
        # Save the original method (for debugging if needed)
        _original_copy = BaseContext.__copy__
        
        def fixed_copy(self):
            """Fixed version of BaseContext.__copy__"""
            # Handle different context types properly
            if isinstance(self, RequestContext):
                # For RequestContext, we need to preserve the request and other attributes
                duplicate = self.__class__(self.request)
                # Copy additional RequestContext attributes
                if hasattr(self, '_processors_index'):
                    duplicate._processors_index = self._processors_index
                if hasattr(self, 'processors'):
                    duplicate.processors = self.processors
                if hasattr(self, 'use_l10n'):
                    duplicate.use_l10n = self.use_l10n
                if hasattr(self, 'use_tz'):
                    duplicate.use_tz = self.use_tz
            else:
                # For regular Context, create new instance
                duplicate = self.__class__()
                # Copy context attributes
                if hasattr(self, 'autoescape'):
                    duplicate.autoescape = self.autoescape
                if hasattr(self, 'use_l10n'):
                    duplicate.use_l10n = self.use_l10n
                if hasattr(self, 'use_tz'):
                    duplicate.use_tz = self.use_tz
                if hasattr(self, 'template_name'):
                    duplicate.template_name = self.template_name
                if hasattr(self, 'render_context'):
                    duplicate.render_context = self.render_context
            
            # Copy the dicts (common to both)
            duplicate.dicts = self.dicts[:]
            return duplicate
        
        # Apply the patch
        BaseContext.__copy__ = fixed_copy
        print("✅ Django BaseContext.__copy__ bug patched successfully!")
        
        # --- Patch 2: RequestContext.new ---
        
        # Save original new method
        _original_new = RequestContext.new
        
        def fixed_new(self, values=None):
            """
            Fixed version of RequestContext.new that ensures _processors_index exists.
            The original implementation deletes it, causing bind_template to fail.
            """
            # Call original new (which creates copy and resets dicts)
            new_context = _original_new(self, values)
            
            # If _processors_index was deleted (which original new does), restore it
            if not hasattr(new_context, '_processors_index'):
                # Initialize placeholders for processors similar to __init__
                new_context._processors_index = len(new_context.dicts)
                new_context.update({}) # placeholder for context processors output
                new_context.update({}) # empty dict for any new modifications
                
            return new_context
            
        # Apply the patch
        RequestContext.new = fixed_new
        print("✅ Django RequestContext.new bug patched successfully!")
        
    except Exception as e:
        print(f"❌ Failed to patch Django template context: {e}")
        import traceback
        traceback.print_exc()

# Apply the patch when this module is imported
patch_django_template_context()