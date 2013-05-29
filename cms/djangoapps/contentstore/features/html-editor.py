#pylint: disable=C0111
#pylint: disable=W0621

from lettuce import world, step


@step('I have created a Blank HTML Page$')
def i_created_blank_common_problem(step):
    world.create_component_instance(
        step, '.large-html-icon', 'i4x://edx/templates/html/Blank_HTML_Page',
        '.xmodule_HtmlModule'
    )


@step('I see only the HTML display name setting$')
def i_see_only_the_html_display_name(step):
    world.verify_all_setting_entries([['Display Name', "Blank HTML Page", True]])
