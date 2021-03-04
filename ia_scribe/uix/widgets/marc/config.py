from ia_scribe.uix.widgets.marc.results_panel.results_panel import MARCResultsPanel
from ia_scribe.uix.widgets.marc.search_panel.search_panel import MARCSearchPanel
from ia_scribe.uix.widgets.marc.loading_panel import LoadingPanel

CONTEXTS = {
            'search': {
                'widget': MARCSearchPanel,
                'title': 'Search',
                'home': True,
                'bindings': {
                    'EVENT_SEARCH_STARTED': ['set_context', 'waiting'],
                    'EVENT_ON_SEARCH_FAILURE': ['set_context', 'search'],
                },
                'properties': {
                        'catalogs_backend': 'catalogs_backend',
                        'search_backend': 'search_backend',
                        'change_title_callback': 'change_title_callback',
                    },
                'action_buttons': {
                        1: {
                            'function': 'toggle_expand',
                            'text': 'Show all'
                        },
                        2: {
                            'function': 'do_search',
                            'text': 'Search',
                        },
                    },
                 },

            'waiting': {
                'widget': LoadingPanel,
                'title': 'Searching...',
                'action_buttons': {
                        1: {
                            'function': None,
                            'text': 'Hidden'
                        },
                        2: {
                            'function': None,
                            'text': 'Hidden'
                        },
                    },
            },
            'results': {
                'widget': MARCResultsPanel,
                'title': 'Results',
                'bindings': {
                    'EVENT_GOT_SEARCH_RESULTS': ['set_context', 'results'],
                    'EVENT_LOAD_MORE_START': ['set_context', 'waiting'],
                    'EVENT_RESULT_SELECT': ['receive_upstream_event_selected'],
                },
                'properties': {
                    'change_title_callback': 'change_title_callback',
                        'search_backend': 'search_backend'
                    },
                'action_buttons': {
                        1: {
                            'function': 'on_go_previous',
                            'text': 'Previous'
                        },
                        2: {
                            'function': 'on_go_next',
                            'text': 'Next'
                        },
                    },
            },

        }
