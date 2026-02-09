# Top-level services package
# Robust proxy loader: support multiple repository layouts.
# 1) Prefer importing RPMT.services (typical development layout)
# 2) Otherwise try to locate a project-local services.py and load it dynamically
# 3) Finally expose a shimbed llm_service if present

import importlib
import importlib.util
from pathlib import Path
import traceback

def _reexport_module(mod):
    for _name, _val in vars(mod).items():
        if _name.startswith('_'):
            continue
        globals().setdefault(_name, _val)

# 1) try to locate a services.py file under project root first (preferred layout for installed servers)
if 'compute_derived' not in globals():
    # look upward from this file for a project root (contains 'templates' or 'modules')
    this_dir = Path(__file__).resolve().parent.parent
    project_root = this_dir
    found_file = None
    for candidate in [project_root, project_root.parent, project_root.parent.parent]:
        try:
            # Prefer a 'services' package directory inside the candidate if present
            pkg_init = Path(candidate) / 'services' / '__init__.py'
            if pkg_init.exists() and not pkg_init.samefile(Path(__file__).resolve()):
                found_file = pkg_init
                found_is_pkg = True
                break
            # Otherwise, fall back to a standalone services.py file
            for p in Path(candidate).rglob('services.py'):
                # ignore the shim file we are editing (services/__init__.py)
                if p.parent.name == 'services' and p.name == 'services.py' and p.samefile(Path(__file__).resolve()):
                    continue
                found_file = p
                found_is_pkg = False
                break
            if found_file:
                break
        except Exception:
            continue
    if found_file:
        try:
            # Load package '__init__.py' if found_is_pkg, otherwise load the single-file services.py
            if found_is_pkg:
                spec = importlib.util.spec_from_file_location('project_services_pkg', str(found_file))
            else:
                spec = importlib.util.spec_from_file_location('project_services', str(found_file))
            proj_mod = importlib.util.module_from_spec(spec)
            # insert into sys.modules so classes/dataclasses see the correct module during execution
            import sys as _sys
            _sys.modules[spec.name] = proj_mod
            try:
                spec.loader.exec_module(proj_mod)  # type: ignore
            finally:
                # leave module in sys.modules for later imports
                pass
            _reexport_module(proj_mod)
            try:
                print(f"services.__init__: dynamically loaded services from {found_file}")
            except Exception:
                pass
            # If the project-level services module does not provide 'llm_service' or it's None,
            # try to load an implementation from the project 'services/llm_service.py' first (preferred),
            # then fall back to RPMT.llm_service if present.
            try:
                need_fill = 'llm_service' not in globals() or globals().get('llm_service') is None
                if need_fill:
                    # project-local services/llm_service.py (recommended layout)
                    try:
                        project_llm = Path(project_root) / 'services' / 'llm_service.py'
                        if project_llm.exists():
                            spec2 = importlib.util.spec_from_file_location('project_llm_service', str(project_llm))
                            mod2 = importlib.util.module_from_spec(spec2)
                            _sys.modules[spec2.name] = mod2
                            spec2.loader.exec_module(mod2)  # type: ignore
                            if getattr(mod2, 'llm_service', None) is not None:
                                globals()['llm_service'] = getattr(mod2, 'llm_service')
                                try:
                                    print('services.__init__: filled llm_service from project services/llm_service.py')
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # last resort: RPMT.llm_service when available
                    if globals().get('llm_service') is None:
                        try:
                            from RPMT.llm_service import llm_service as _rpmtsvc  # type: ignore
                            globals()['llm_service'] = _rpmtsvc
                            try:
                                print('services.__init__: filled llm_service from RPMT.llm_service (project-level was absent)')
                            except Exception:
                                pass
                        except Exception:
                            # ignore failures; keep project's None if rpmtsvc not available
                            pass
            except Exception:
                pass
        except Exception as e:
            print('services.__init__: failed to dynamically load services.py at', found_file)
            traceback.print_exc()
# 2) try RPMT.services as a fallback (development layout)
_rpmtsrv = None
try:
    _rpmtsrv = importlib.import_module('RPMT.services')
    _reexport_module(_rpmtsrv)
except Exception:
    _rpmtsrv = None
# 3) Re-export llm_service from the shim or the loaded module
try:
    # Prefer a local services.llm_service if a submodule exists
    from .llm_service import llm_service  # type: ignore
except Exception:
    # If not available, try to use any llm_service imported from a project-level services.py
    llm_service = globals().get('llm_service', None)
    # As a final fallback, attempt to import from RPMT package (common layout)
    if llm_service is None:
        try:
            from RPMT.llm_service import llm_service as _rpmtsvc  # type: ignore
            llm_service = _rpmtsvc
            try:
                print('services.__init__: re-exported llm_service from RPMT.llm_service')
            except Exception:
                pass
        except Exception:
            # leave llm_service as None if nothing found
            llm_service = globals().get('llm_service', None)
    # still try to ensure name exists
    if llm_service is None and 'llm_service' in globals():
        llm_service = globals()['llm_service']

# Provide lazy attribute access so callers can retrieve llm_service even if it
# wasn't available at import time (try importing RPMT.llm_service on first access).
def __getattr__(name: str):
    if name == 'llm_service':
        # Try to import RPMT.llm_service and cache it
        try:
            from RPMT.llm_service import llm_service as _rpmtsvc  # type: ignore
            globals()['llm_service'] = _rpmtsvc
            try:
                print('services.__init__: lazily imported llm_service from RPMT.llm_service')
            except Exception:
                pass
            return _rpmtsvc
        except Exception as e:
            # store last import error for diagnostics
            globals().setdefault('__llm_import_error__', e)
            raise AttributeError(f"llm_service is not available: {e}") from e
    raise AttributeError(name)

# diagnostic print if compute_derived still missing
if 'compute_derived' not in globals():
    try:
        print('services.__init__: compute_derived not re-exported by any candidate (RPMT.services / services.py)')
    except Exception:
        pass
