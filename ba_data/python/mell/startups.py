import sys
import os
import traceback
import datetime
import shutil
from pathlib import Path
from mell.resource_packs import (
    ResourcePack, 
    apply_resource_pack, 
    clear_resource_packs,
)

class CoreStartup():
    def __init__(self):
        externals_dir = os.path.join(
            os.path.dirname(__file__).replace('\\mell', ''),
            'externals'
        )

        if externals_dir not in sys.path:
            sys.path.insert(0, externals_dir)
        
        def my_global_exception_hook(exc_type, exc_value, exc_traceback):
            import bauiv1 as bui
            global _last_error_time, _recent_error

            # convert a error to text
            error_text = ''.join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
            
            _last_error_time = datetime.datetime.now()
            _recent_error = True
            # Log it somewhere visible
            print(error_text)
            bui.getsound('error').play()
        sys.excepthook = my_global_exception_hook

class GameStartup():
    def __init__(self):
        import babase as ba
        import bascenev1 as bs
        import bauiv1 as bui
        from bascenev1lib.mainmenu import MainMenuSession
        
        def auto_module_import():
            globals = sys.modules['__main__'].__dict__
            globals['ba'] = ba
            globals['bs'] = bs
            globals['bui'] = bui
            globals['ga'] = bs.getactivity
            globals['gp'] = lambda: bs.getactivity().players
            globals['gs'] = bs.getsession
        auto_module_import()
        def start_rpc():
            from .discordrp_handler import RichPresence
            RichPresence()
        ba.apptimer(3, start_rpc)
        # make sure some folders and lists exist,
        # create if otherwise
        mods_dir = Path(bui.app.env.python_directory_user)
        packs_list = getattr(ba.app, 'resource_packs', None)
        invalid_res_packs = []
        if not packs_list:
            ba.app.resource_packs = []
            packs_list = ba.app.resource_packs
        # look for resource packs folder inside mods dir
        if mods_dir.is_dir():
            packs_dir = mods_dir / 'resource_packs'
            # okay... doesn't exist. lets make it a directory
            if not packs_dir.is_dir():
                Path.mkdir(packs_dir)
            for file in packs_dir.iterdir():
                try:
                    pack = ResourcePack(file)
                    packs_list.append(pack)
                except Exception as exc:
                    print(f'Invalid resource pack; {file}\nError: {exc}')
                    invalid_res_packs.append(str(file))
                    continue
        else:
            print("Mods dir doesn't exist...???")
        # If we have invalid resource packs,
        # inform our user of such inconvenience
        if invalid_res_packs:
            packs_joined = '\n'.join(invalid_res_packs)
            text = bui.Lstr(
                resource='userInvalidResourcePacks',
                subs=[
                    ('${PACKS}', packs_joined),
                ]
            )
            ba.apptimer(2, ba.CallPartial(ba.screenmessage, text, color=(1, 0, 0)))
            ba.apptimer(2, bui.getsound('error').play)
        # issue a restart on our assets
        bui.app.classic.run_media_reload_benchmark()
        # FINALLY, launch the main menu
        ba.apptimer(2, bs.app.classic.return_to_main_menu_session_gracefully)