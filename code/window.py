import asyncio
import sys

import pygame
import pygame_menu
from settings import *
from save_load import *
from timers import Timer
from options_values import *
from simulation import *
from functions import animation_text_save
from async_menu import run_menu


_YIELD_ON_WEB = sys.platform == 'emscripten'


def _selected_menu_value(data, key):
    value = data.get(key)

    try:
        return value[0][0]
    except Exception:
        return str(value)


def _format_gene(gene_id):
    return GENE_LABELS.get(gene_id, gene_id)


def _normalise_gene_search_text(value):
    """Normalise gene search text so b1241, 1241, adhE or adh e all match."""
    return ''.join(
        char.lower()
        for char in str(value)
        if char.isalnum()
    )


def _gene_matches_search(gene_id, search_text):
    query = _normalise_gene_search_text(search_text)
    if not query:
        return True

    gene_name = GENE_NAMES.get(gene_id, '')
    gene_label = GENE_LABELS.get(gene_id, gene_id)
    gene_number = gene_id[1:] if gene_id.startswith('b') else gene_id

    searchable_values = (
        gene_id,
        gene_number,
        gene_name,
        gene_label,
        f'{gene_id}{gene_name}',
        f'{gene_name}{gene_id}',
    )

    return any(
        query in _normalise_gene_search_text(value)
        for value in searchable_values
    )


def _build_clean_gene_data(raw_gene_data):
    """Keep only real model genes, ignoring UI-only widgets like the search box."""
    return {
        gene_id: bool(raw_gene_data.get(gene_id, True))
        for gene_id in GENES
    }


def _build_gene_summary(genes):
    knocked_out_genes = [
        gene_id for gene_id, is_active in genes.items()
        if not is_active
    ]

    if not knocked_out_genes:
        return 'No gene knockouts.'

    return '\n'.join(
        f'- {_format_gene(gene_id)}'
        for gene_id in knocked_out_genes
    )


def _build_environmental_summary(reactions):
    changed_conditions = []
    reaction_values = list(reactions.values())

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = reaction_values[lb_index]
        upper_bound_open = reaction_values[ub_index]

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        if (
            lower_bound_open != default_lower_bound_open
            or upper_bound_open != default_upper_bound_open
        ):
            reaction_id = REACTIONS.index[i]
            reaction_name = REACTIONS.name.iloc[i]

            lower_bound_value = -1000 if lower_bound_open else 0
            upper_bound_value = 1000 if upper_bound_open else 0

            changed_conditions.append(
                f'- {reaction_name} ({reaction_id}): '
                f'Lower Bound {"Open" if lower_bound_open else "Closed"} ({lower_bound_value}), '
                f'Upper Bound {"Open" if upper_bound_open else "Closed"} ({upper_bound_value})'
            )

    if not changed_conditions:
        return 'No environmental changes.'

    return '\n'.join(changed_conditions)



def _build_clean_production_flux_data(raw_flux_data):
    """Keep only curated production flux toggles from the menu input data."""
    raw_flux_data = raw_flux_data or {}
    return {
        option['id']: bool(raw_flux_data.get(option['id'], False))
        for option in PRODUCTION_FLUX_OPTIONS
    }


def _selected_production_flux_ids(production_flux_data):
    return [
        option['id']
        for option in PRODUCTION_FLUX_OPTIONS
        if bool(production_flux_data.get(option['id'], False))
    ]


def _build_production_flux_summary(production_flux_data):
    selected_ids = _selected_production_flux_ids(production_flux_data)
    if not selected_ids:
        return 'No production fluxes selected.'

    return '\n'.join(
        f"- {PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)}"
        for reaction_id in selected_ids
    )


def _build_production_fluxes_text(production_fluxes):
    if not production_fluxes or not production_fluxes.get('selected_ids'):
        return ''

    lines = [
        'Production fluxes tracked:',
        '(positive exchange flux = product secreted/exported)'
    ]

    if production_fluxes.get('error'):
        lines.append(f"Error: {production_fluxes.get('error')}")
        return '\n'.join(lines)

    items = production_fluxes.get('items') or []
    if not items:
        lines.append('No flux values were returned for the selected products.')
        return '\n'.join(lines)

    for item in items:
        label = item.get('label') or item.get('reaction_id')
        if item.get('error'):
            lines.append(f"- {label}: not available")
        else:
            lines.append(f"- {label}: {float(item.get('production_flux', 0.0)):.3f}")

    return '\n'.join(lines)


def _build_simulation_results_text(results):
    try:
        objective_name = results[0]
        objective_result = results[1]
    except Exception:
        return str(results)

    text = (
        'Objective flux:\n'
        f'{objective_name}: {objective_result}'
    )

    production_text = ''
    try:
        production_text = _build_production_fluxes_text(results[2])
    except Exception:
        production_text = ''

    if production_text:
        text += '\n\n' + production_text

    return text





def _build_mission04_text(production_data):
    if not production_data:
        return ''

    if production_data.get('error'):
        return f"Mission 04 Production Check\nError: {production_data.get('error')}"

    environment_note = (
        'Environmental conditions were changed. For Mission 04, keep them unchanged.'
        if production_data.get('environment_changed')
        else 'Environmental conditions unchanged.'
    )
    status = (
        'Production improved. This knockout looks promising.'
        if production_data.get('improved')
        else 'No improvement yet. Try a different candidate knockout.'
    )
    change = float(production_data.get('production_change', 0))
    change_prefix = '+' if change > 0 else ''

    return (
        'Mission 04 Production Check\n\n'
        f"Target product: {production_data.get('product_name')} ({production_data.get('production_objective')})\n"
        f"Baseline {production_data.get('product_name')} flux: {float(production_data.get('baseline_production', 0)):.3f}\n"
        f"Current {production_data.get('product_name')} flux: {float(production_data.get('current_production', 0)):.3f}\n"
        f"Production change: {change_prefix}{change:.3f}\n"
        f"Current growth: {float(production_data.get('current_growth', 0)):.3f}\n\n"
        f"{environment_note}\n"
        f"{status}"
    )


def _build_mission05_text(production_data):
    if not production_data:
        return ''

    if production_data.get('error'):
        return f"Mission 05 Production Check\nError: {production_data.get('error')}"

    oxygen_note = (
        f"O2 lower bound closed ({production_data.get('oxygen_reaction')}): yes."
        if production_data.get('oxygen_disabled')
        else f"O2 is still available. Close the lower bound of {production_data.get('oxygen_reaction')}."
    )
    status = (
        'Lactate production improved. This combination looks promising.'
        if production_data.get('oxygen_disabled') and production_data.get('improved')
        else 'Not enough yet. Combine anaerobiosis with the right knockout.'
    )
    change = float(production_data.get('production_change', 0))
    change_prefix = '+' if change > 0 else ''

    return (
        'Mission 05 Production Check\n\n'
        f"Target product: {production_data.get('product_name')} ({production_data.get('production_objective')})\n"
        f"Anaerobic baseline flux: {float(production_data.get('baseline_production', 0)):.3f}\n"
        f"Current {production_data.get('product_name')} flux: {float(production_data.get('current_production', 0)):.3f}\n"
        f"Production change: {change_prefix}{change:.3f}\n"
        f"Current growth: {float(production_data.get('current_growth', 0)):.3f}\n\n"
        f"{oxygen_note}\n"
        f"{status}"
    )


def _build_challenge_text(challenge_data):
    if not challenge_data:
        return ''

    if challenge_data.get('error'):
        return f"Mission 06 Challenge\nError: {challenge_data.get('error')}"

    status = 'You win!' if challenge_data.get('win') else 'You need a better balance between growth and ethanol production.'
    return (
        'Mission 06 Challenge\n\n'
        f"Growth ({challenge_data.get('growth_objective')}): {float(challenge_data.get('growth', 0)):.3f}\n"
        f"Ethanol production flux ({challenge_data.get('production_objective')}): {float(challenge_data.get('production', 0)):.3f}\n"
        f"Your score: {float(challenge_data.get('score', 0)):.3f}\n"
        f"Villain score: {float(challenge_data.get('villain_score', 0)):.3f}\n\n"
        f"{status}"
    )

def _add_summary_section(menu, title, text):
    menu.add.label(title, font_size=32, font_color=(20, 0, 150))
    menu.add.vertical_margin(10)
    menu.add.label(
        text,
        wordwrap=True,
        padding=(20, 20, 20, 20),
        background_color='white',
        font_size=24
    )
    menu.add.vertical_margin(25)

class Window:
    def __init__(self, toggle_menu, player) -> None:

        # general setup
        self.player = player
        self.toggle_menu = toggle_menu
        self.display_surface = pygame.display.get_surface()
        # font_path = get_resource_path('font/LycheeSoda.ttf')
        # font2_path = get_resource_path('font/NotoColorEmoji-Regular.ttf')
        # self.font = pygame.font.Font(font_path,30)
        self.results = ''

        # self.index = 0
        self.timer = Timer(200)



    async def setup(self):

        ecoli_rip = get_resource_path('graphics/environment/ecoli_rip.jpg')
        
        menu = pygame_menu.Menu(
            height=720,
            onclose=self.toggle_menu,
            theme=mytheme,
            title='Simulation Menu',
            width=1280,
        )

        menu_genes = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Genes',
            width=1280
        )


        menu_reactions = pygame_menu.Menu(
            height=720,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Environmental Conditions',
            width=1280
        )

        # MENU REACTIONS
        menu_reactions.add.vertical_margin(50)
        menu_reactions.add.label("TIP for Mission 02:\nThe lower bound tells the cell if it can reverse the reaction and do it the opposite way (e.g., taking in nutrients).\nThe upper bound tells it how fast or how much of the reaction can happen in the forward direction (e.g., producing metabolites).",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
        menu_reactions.add.vertical_margin(20)
        # Reactions (Range slider) // pode-se alterar as bounds para text inputs de forma a alterar para 0,0 (com range slider não é possível)
        for i in range(len(REACTIONS.name)):
            menu_reactions.add.label(REACTIONS.name.iloc[i])
            if REACTIONS.lb.iloc[i] != 0:
                default_lb_bool = True
            else:
                default_lb_bool = False
            if REACTIONS.ub.iloc[i] != 0:
                default_ub_bool = True
            else:
                default_ub_bool = False
            menu_reactions.add.toggle_switch('Lower Bound',default_lb_bool, onchange=None, state_text=('Closed', 'Open'), state_text_font_size=20, font_size = 24, state_color=('grey','gold'), state_text_font_color=('black', 'black')) #, kwargs=txt, toggleswitch_id=txt)
            menu_reactions.add.toggle_switch('Upper Bound',default_ub_bool, onchange=None, state_text=('Closed', 'Open'), state_text_font_size=20, font_size = 24, state_color=('grey','gold'), state_text_font_color=('black', 'black')) #, kwargs=txt, toggleswitch_id=txt)
            # menu_reactions.add.range_slider('Lower Bound', REACTIONS.lb[i], (-1000,0), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]+'lb') #, rangeslider_id=OPTIONS['Reactions'][i])
            # menu_reactions.add.range_slider('Upper Bound', REACTIONS.ub[i], (0, 1000), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]+'ub') #, rangeslider_id=OPTIONS['Reactions'][i])

            menu_reactions.add.vertical_margin(30)

            if _YIELD_ON_WEB and (i + 1) % 4 == 0:
                await asyncio.sleep(0)
        menu_reactions.add.vertical_margin(20)
        menu_reactions.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_reactions.add.vertical_margin(20)

        # menu_reactions_backup = pygame_menu.Menu(
        #     height=720,
        #     onclose=pygame_menu.events.BACK,
        #     theme=mytheme,
        #     title='Environmental Conditions',
        #     width=1280
        # )

        # # MENU REACTIONS
        # menu_reactions_backup.add.vertical_margin(50)
        # # Reactions (Range slider) // pode-se alterar as bounds para text inputs de forma a alterar para 0,0 (com range slider não é possível)  
        
        # for i in range(len(REACTIONS.name)):
        #     menu_reactions_backup.add.range_slider(REACTIONS.name[i], (REACTIONS.lb[i],REACTIONS.ub[i]), (-1000, 1000), 10, font_size=30, range_box_color = 'gold', rangeslider_id=REACTIONS.index[i]) #, rangeslider_id=OPTIONS['Reactions'][i])
        #     menu_reactions_backup.add.toggle_switch('Bounds',True, onchange=None, state_text=('Deactivated', 'Active'), state_text_font_size=20, font_size = 24, state_color=('grey','gold')) #, kwargs=txt, toggleswitch_id=txt)
        #     menu_reactions_backup.add.vertical_margin(30)
        # menu_reactions_backup.add.vertical_margin(20)
        # menu_reactions_backup.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        # menu_reactions_backup.add.vertical_margin(20)



        # def toggle_reaction(txt, **id):
        #     if not txt:
        #         REACTIONS.lb[i] = 0
        #         REACTIONS.ub[i] = 0
        #     else:
        #         pass

        # MENU SUB (Genes)
        menu_genes.add.vertical_margin(50)
        # menu_genes.add.label('TIP')
        menu_genes.add.label("TIP for Mission 03, Mission 04 and Mission 05: \nSome genes are essential for survival. Others can redirect metabolism toward useful products. Try one highlighted gene knockout at a time.",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
        menu_genes.add.vertical_margin(20)

        menu_genes.add.label(
            "Search by gene id, number or name. Examples: b1241, 1241, adhE, pta. Use Reset Genes to reactivate all genes.",
            wordwrap=True,
            padding=(20, 20, 20, 20),
            background_color="white",
            font_size=24
        )
        menu_genes.add.vertical_margin(10)

        gene_toggle_widgets = {}
        gene_search_input = None
        gene_search_status = menu_genes.add.label(
            f"Showing all {len(GENES)} genes.",
            font_size=22,
            font_color=(20, 0, 150)
        )

        def apply_gene_search(search_text=None, **_kwargs):
            current_search = '' if search_text is None else str(search_text)
            if search_text is None and gene_search_input is not None:
                current_search = str(gene_search_input.get_value())

            visible_count = 0
            for gene_id, widget in gene_toggle_widgets.items():
                if _gene_matches_search(gene_id, current_search):
                    widget.show()
                    visible_count += 1
                else:
                    widget.hide()

            if current_search.strip():
                gene_search_status.set_title(
                    f"Search: {current_search} | {visible_count} gene(s) found."
                )
            else:
                gene_search_status.set_title(f"Showing all {len(GENES)} genes.")

        def clear_gene_search(*_args, **_kwargs):
            if gene_search_input is not None:
                gene_search_input.set_value('')
            apply_gene_search('')

        def reset_gene_toggles(*_args, **_kwargs):
            """Reactivate every gene and restore the genes page to its default state."""
            for widget in gene_toggle_widgets.values():
                widget.set_value(True)

            if gene_search_input is not None:
                gene_search_input.set_value('')
            apply_gene_search('')
            gene_search_status.set_title(f"All {len(GENES)} genes are active again.")

        gene_search_input = menu_genes.add.text_input(
            'Search gene: ',
            default='',
            input_underline='_',
            maxchar=30,
            maxwidth=30,
            onchange=apply_gene_search,
            onreturn=apply_gene_search,
            textinput_id='gene_search',
            background_color="white",
            font_color=(20, 0, 150)
        )
        menu_genes.add.vertical_margin(10)
        menu_genes.add.button(
            'Search / Refresh',
            apply_gene_search,
            font_color='white',
            background_color=(20, 100, 100)
        )
        menu_genes.add.button(
            'Clear Search',
            clear_gene_search,
            font_color='white',
            background_color=(70, 70, 70)
        )
        menu_genes.add.button(
            'Reset Genes',
            reset_gene_toggles,
            font_color='white',
            background_color=(150, 40, 40)
        )
        menu_genes.add.vertical_margin(20)

        genes_03 = ['b1241','b3115','b3736','b2975','b1524','b2278','b2926','b2297','b0728','b3919']
        genes_04 = MISSION04_CANDIDATE_GENES
        genes_05 = MISSION05_CANDIDATE_GENES

        for i, gene_id in enumerate(GENES):
            gene_label = GENE_LABELS.get(gene_id, gene_id)

            if gene_id in genes_03 or gene_id in genes_04 or gene_id in genes_05:
                gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                    gene_label,
                    True,
                    kwargs=gene_id,
                    toggleswitch_id=gene_id,
                    background_color="gold",
                    font_color="black"
                )
            else:
                gene_toggle_widgets[gene_id] = menu_genes.add.toggle_switch(
                    gene_label,
                    True,
                    kwargs=gene_id,
                    toggleswitch_id=gene_id
                )

            if _YIELD_ON_WEB and (i + 1) % 8 == 0:
                await asyncio.sleep(0)

        apply_gene_search('')
        menu_genes.add.vertical_margin(20)
        menu_genes.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_genes.add.vertical_margin(20)


        # MENU RESULTS
        # menu_results = pygame_menu.Menu(
        #     height=720,
        #     onclose=pygame_menu.events.BACK,
        #     theme=mytheme,
        #     title='History of Past Simulations',
        #     width=1280
        # )
        # menu_results.add.vertical_margin(20)
        # try:
        #     res_path = get_resource_path('code/player_history/results')
        #     res = load_file(res_path)

        #     menu_results.add.label(res)
        # except FileNotFoundError:
        #     menu_results.add.label('You have to make at least one simulation to see results.')


        
        

        # MENU SUB (Production Flux)
        menu_production_flux = pygame_menu.Menu(
            height=720,
            center_content=False,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Production Flux',
            width=1280
        )

        menu_production_flux.add.vertical_margin(40)
        menu_production_flux.add.label(
            "Select the product fluxes you want to measure after each simulation.\nThis does not change the Objective; it only tracks the selected exchange fluxes in New Results.",
            wordwrap=True,
            padding=(20, 30, 20, 30),
            background_color="white",
            font_size=26
        )
        menu_production_flux.add.vertical_margin(20)

        production_flux_widgets = {}

        def clear_production_fluxes(*_args, **_kwargs):
            for widget in production_flux_widgets.values():
                widget.set_value(False)

        if PRODUCTION_FLUX_OPTIONS:
            for option in PRODUCTION_FLUX_OPTIONS:
                production_flux_widgets[option['id']] = menu_production_flux.add.toggle_switch(
                    option['label'],
                    False,
                    toggleswitch_id=option['id'],
                    state_text=('Off', 'On'),
                    state_text_font_size=20,
                    font_size=24,
                    state_color=('grey', 'gold'),
                    state_text_font_color=('black', 'black')
                )
                menu_production_flux.add.vertical_margin(10)
        else:
            menu_production_flux.add.label(
                'No curated production fluxes are available for this model.',
                wordwrap=True,
                padding=(20, 20, 20, 20),
                background_color='white',
                font_size=24
            )

        menu_production_flux.add.vertical_margin(20)
        menu_production_flux.add.button(
            'Clear Production Fluxes',
            clear_production_fluxes,
            font_color='white',
            background_color=(150, 40, 40)
        )
        menu_production_flux.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))
        menu_production_flux.add.vertical_margin(20)


        # MENU SUB OBJECTIVE
        menu_objective = pygame_menu.Menu(
            height=720,
            onclose=pygame_menu.events.BACK,
            theme=mytheme,
            title='Objective',
            width=1280
        )

        objectives = []
        default_obj = 0
        # print(str(objective))
        
        for i in range(len(REACTIONS_v0)):
            if REACTIONS_v0.index[i] == str(objective):
                default_obj = i
            objectives.append((REACTIONS_v0.index[i], REACTIONS_v0.index[i]))
        
        menu_objective.add.dropselect(title='Objective: ',
                                   items=objectives,
                                   default=default_obj,
                                   selection_box_height=8,
                                   selection_box_width=500,
                                   dropselect_id='objective')
        # menu_objective.add.range_slider('Fraction', default=90, range_values=(0,100), increment=1, rangeslider_id='obj_fraction')

        menu_objective.add.vertical_margin(30)
        menu_objective.add.label("TIP: \nBy default, you want \"Biomass” to be set as the objective because you want to see if E. Coli can grow or even survive in the environment you create.",
                                #  max_char=1,
                                 wordwrap=True,
                                #  align=pygame_menu.locals.ALIGN_CENTER,
                                #  margin=(20, 0),
                                 padding = (20,30,20,30),
                                 background_color = "white",
                                 font_size = 26)
        menu_objective.add.vertical_margin(20)
        menu_objective.add.label(
            'Production Flux:',
            font_size=30,
            font_color=(20, 0, 150)
        )
        menu_objective.add.button(
            'Select production fluxes to track',
            menu_production_flux,
            font_color='white',
            background_color=(20, 100, 100)
        )
        menu_objective.add.vertical_margin(20)
        menu_objective.add.button('Back', pygame_menu.events.BACK, background_color=(70, 70, 70))

        

        def data_fun() -> None:
            """
            Print data of the menu.
            """

            # MENU AFTER SIMULATION RESULTS
            menu_simul = pygame_menu.Menu(
                height=720,
                onclose=self.toggle_menu,
                theme=mytheme,
                title='New Results',
                width=1280,
                menu_id='menu_new_results'
            )

            data_simul = menu.get_input_data()
            data_objective = menu_objective.get_input_data()
            raw_data_genes = menu_genes.get_input_data()
            data_genes = _build_clean_gene_data(raw_data_genes)
            data_reac = menu_reactions.get_input_data()
            data_fluxes = _build_clean_production_flux_data(menu_production_flux.get_input_data())



            menu_summary = pygame_menu.Menu(
                height=720,
                center_content=False,
                onclose=pygame_menu.events.BACK,
                theme=mytheme,
                title='Simulation Summary',
                width=1280,
                menu_id='menu_simulation_summary'
            )

            simulation_method = _selected_menu_value(data_simul, 'method')
            objective_name = _selected_menu_value(data_objective, 'objective')

            menu_summary.add.vertical_margin(30)

            _add_summary_section(
                menu_summary,
                'General setup',
                f'Simulation method: {simulation_method}\nObjective: {objective_name}'
            )

            _add_summary_section(
                menu_summary,
                'Gene knockouts',
                _build_gene_summary(data_genes)
            )

            _add_summary_section(
                menu_summary,
                'Environmental changes',
                _build_environmental_summary(data_reac)
            )

            _add_summary_section(
                menu_summary,
                'Production fluxes to track',
                _build_production_flux_summary(data_fluxes)
            )

            menu_summary.add.button(
                'Back',
                pygame_menu.events.BACK,
                background_color=(70, 70, 70)
            )


            save_simulation_file([data_simul, data_objective, data_genes, data_reac, data_fluxes])
            animation_text_save('Running')
            if sys.platform == 'emscripten':
                self.results = run_simul_remote(BACKEND_URL)
            else:
                self.results = run_simul()

            mission04_data = None
            if '04' in self.player.missions_activated and '04' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission04_data = run_mission04_production_check_remote(BACKEND_URL)
                else:
                    mission04_data = run_mission04_production_check()

            mission05_data = None
            if '05' in self.player.missions_activated and '05' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    mission05_data = run_mission05_production_check_remote(BACKEND_URL)
                else:
                    mission05_data = run_mission05_production_check()

            challenge_data = None
            if '06' in self.player.missions_activated and '06' not in self.player.missions_completed:
                if sys.platform == 'emscripten':
                    challenge_data = run_challenge_score_remote(BACKEND_URL)
                else:
                    challenge_data = run_challenge_score()

            self.player.results.insert(0,self.results)
            try:
                menu.remove_widget('new_results')
                menu.remove_widget('menu_new_results')
            except:
                # print('teste2')
                pass
            
            menu_simul.add.label("Results:")
            menu_simul.add.vertical_margin(50)  # Adds margin
            
            menu.add.button('New Results', action=menu_simul, font_color = 'white', background_color=(0,150,50), button_id='new_results')
            result_display_text = _build_simulation_results_text(self.results)
            menu_simul.add.label(result_display_text, label_id='results')
            save_results(result_display_text)
            save_file(self.player.get_save_data())
            menu_simul.add.vertical_margin(50, margin_id='nr_margin')
            menu_simul.add.button(
                'Simulation Summary',
                menu_summary,
                font_color='white',
                background_color=(20, 100, 100),
                button_id='simulation_summary'
            )
            menu_simul.add.vertical_margin(20)

            if mission04_data is not None:
                menu_simul.add.label(
                    _build_mission04_text(mission04_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission04_production_check'
                )
                menu_simul.add.vertical_margin(20)

            if mission05_data is not None:
                menu_simul.add.label(
                    _build_mission05_text(mission05_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission05_production_check'
                )
                menu_simul.add.vertical_margin(20)

            if challenge_data is not None:
                menu_simul.add.label(
                    _build_challenge_text(challenge_data),
                    wordwrap=True,
                    padding=(20, 20, 20, 20),
                    background_color='white',
                    font_size=24,
                    label_id='mission06_challenge'
                )
                menu_simul.add.vertical_margin(20)

            if self.results[1] == 'Status: INFEASIBLE' or self.results[1] == 0.0 or self.results[1] == -0.0:
                menu_simul.add.image(ecoli_rip, scale=(0.5, 0.5), image_id='ecolidead')
                menu_simul.add.vertical_margin(50, margin_id='deadmargin')
            else:
                try:
                    menu_simul.remove_widget('ecolidead')
                except:
                    pass
                try:
                    menu_simul.remove_widget('deadmargin')
                except:
                    pass
            menu_simul.add.button('Close', pygame_menu.events.BACK, background_color=(70, 70, 70), button_id='nr_close')


        # def restore_data() -> None:
        #     """
        #     """
        #     menu.reset_value()
        #     menu_objective.reset_value()
        #     menu_genes.reset_value()
        #     menu_reactions.reset_value()


        menu.add.label('TIP: See Book "How to Simulate"', font_size = 20)
        menu.add.vertical_margin(20)
        menu.add.label('Change options: ', font_size = 40)
        menu.add.vertical_margin(20)

        menu.add.dropselect(title='Simulation Method ',
                            items=[('FBA', 'fba'),
                                   ('pFBA', 'pfba'),
                                #    ('MOMA', 'moma'),
                                   ('lMOMA', 'lmoma'),
                                   ('ROOM','room')],
                                   default=0,
                                   selection_box_height=5, dropselect_id='method', background_color="white", font_color=(20,0,150))
        menu.add.button('Objective', menu_objective, font_color = (20,0,150), background_color="white")
        menu.add.button('Production Flux', menu_production_flux, font_color = (20,0,150), background_color="white")
        menu.add.button('Genes', menu_genes, font_color = (20,0,150), background_color="white")
        menu.add.button('Environmental Conditions', menu_reactions, font_color = (20,0,150), background_color="white")
        # menu.add.button('Environmental Conditions', menu_reactions_backup, font_color = (20,0,150), background_color="white")
        menu.add.vertical_margin(50)  # Adds margin
        # menu.add.button('Restore Data', restore_data, background_color=(100,0,0))
        # menu.add.vertical_margin(20)  # Adds margin

        menu.add.button('Run Simulation', action=data_fun, font_color = 'white', background_color=(20,100,100))
        menu.add.vertical_margin(20)  # Adds margin
        # last_results = menu.add.button('Results Log', action=menu_results, font_color = 'black', background_color="grey")
        # menu.add.vertical_margin(50)  # Adds margin

        def check_escape():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] and menu.is_enabled():
                menu.close()

        await run_menu(menu, self.display_surface, on_update=check_escape)




    def input(self):
        keys = pygame.key.get_pressed()
        self.timer.update()

        if keys[pygame.K_ESCAPE]:
            pass  # ESC is handled by pygame-menu's onclose callback


    async def update(self):
        self.input()
        await self.setup()

