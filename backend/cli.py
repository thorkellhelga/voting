#coding:utf-8
"""
Command line interface for Voting.
"""
import click
import tabulate

import voting
import simulate as sim
import util
import web

### Monkey patching CSV output mode into tabulate:
tabulate.tabulate_formats.append("csv")
tabulate._table_formats["csv"] = tabulate.TableFormat(
    lineabove=None, linebelowheader=None, linebetweenrows=None,
    linebelow=None, headerrow=tabulate.DataRow(begin=u'', sep=u',', end=u''),
    datarow=tabulate.DataRow(begin=u'', sep=u',', end=u''),
    padding=0, with_header_hide=None)


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    """Basic CLI."""
    if debug:
        click.echo('Debug mode is on')

@cli.command()
@click.option('--votes', required=True, type=click.Path(exists=True),
                help='File with vote data to use as seed')
@click.option('--constituencies', required=True, type=click.Path(exists=True),
                help='File with constituency data')
@click.option('--test_method', type=click.STRING,
                help='The method to be tested')
@click.option('--simulation_count', type=click.INT, default=10000,
                help='Number of simulations to run')
@click.option('--gen_method', type=click.Choice(sim.GENERATING_METHODS.keys()),
                default="beta", help='Method to generate votes')
@click.option('--var_param', type=click.FLOAT, default=0.1)
@click.option('--to_xlsx', type=click.STRING)
@click.option('--show-details', default=False, is_flag=True)
def simulate(votes, constituencies, **kwargs):
    """Simulate elections."""
    e_rules = voting.ElectionRules()
    e_rules["constituencies"] = constituencies
    parties, votes = util.load_votes(votes, e_rules["constituencies"])
    e_rules["parties"] = parties
    election = voting.Election(e_rules, votes)
    s_rules = sim.SimulationRules()

    try:
      for arg, val in kwargs.iteritems():
        s_rules[arg] = val
    except AttributeError:
      for arg, val in kwargs.items():
        s_rules[arg] = val


    e_rules = util.sim_election_rules(e_rules, s_rules["test_method"])

    simulation = sim.Simulation(s_rules, election)

    simulation.simulate()

    if s_rules["show_details"]:
        util.print_simulation(simulation)
    if s_rules["to_xlsx"]:
        util.simulation_to_xlsx(simulation, s_rules["to_xlsx"])

    # divider, adjustment_divider, constituencies, votes, voters,
    # simulations, threshold, betavariancesquared, partyweight, output,
    # adjustment_method

    # 1. Setup:
    #  - Load data files
    #  - Select methods
    # threshold *= 0.01
    # const = util.load_constituencies(constituencies)
    # parties, votes = util.load_votes(votes, const)
    #
    # divmethod = voting.DIVIDER_RULES[divider]
    # if not adjustment_divider:
    #     adjustment_divmethod = divmethod
    # else:
    #     adjustment_divmethod = voting.DIVIDER_RULES[adjustment_divider]
    #
    # for sim in range(simulations):
    #     print "\rSimulation %d" % sim,
    #     sys.stdout.flush()
    #
    #     for meth in adjustment_method:
    #         method = voting.ADJUSTMENT_METHODS[meth]
    #
    #         results = method(votes, v_const_seats, v_party_adjustment_seats,
    #                          m_allocations, adjustment_divmethod, threshold)

    # Output:
    #  - delta of entropy from optimal
    #  - delta of seats from optimal
    #  - smallest number of votes behind a seat
    #  - largest number of votes behind a seat
    #

@cli.command()
@click.argument('rules', required=True,
                type=click.Path(exists=True))
def script(rules, **kwargs):
    """Read from a script file and execute its commands."""
    election = voting.run_script(rules)
    util.pretty_print_election(election)


@cli.command()
@click.option('--host', required=False)
@click.option('--port', required=False, type=click.INT)
def www(host="localhost", port=5000, **kwargs):
    web.app.debug = True
    web.app.run(debug=True, host=host, port=port)


@cli.command()
@click.option('--divider', required=True,
              type=click.Choice(voting.DIVIDER_RULES.keys()),
              help='Divider rule to use.')
@click.option('--adjustment-divider', default=None, required=False,
              type=click.Choice(voting.DIVIDER_RULES.keys()),
              help='Divider rule for adjustment seats. Defaults to primary.')
@click.option('--constituencies', required=True, type=click.Path(exists=True),
              help='File with constituency data')
@click.option('--votes', required=True, type=click.Path(exists=True),
              help='File with vote data')
@click.option('--threshold', default=5,
              help='Threshold (in %%) for adjustment seats')
@click.option('--output', default='simple',
              type=click.Choice(tabulate.tabulate_formats))
@click.option('--show-entropy', default=False, is_flag=True)
@click.option('--show-details', default=False, is_flag=True)
@click.option('--to-xlsx', type=click.STRING)
@click.option('--adjustment-method', '-m',
              type=click.Choice(voting.ADJUSTMENT_METHODS.keys()),
              required=True)
@click.option('--show-constituency-seats', is_flag=True)
def apportion(votes, **kwargs):
    """Do regular apportionment based on votes and constituency data."""
    rules = voting.ElectionRules()
    kwargs["adjustment_divider"] = kwargs["adjustment_divider"] or kwargs["divider"]
    try:
      for arg, val in kwargs.iteritems():
        rules[arg] = val
    except AttributeError:
      for arg, val in kwargs.items():
        rules[arg] = val

    parties, votes = util.load_votes(votes, rules["constituencies"])
    rules["parties"] = parties
    election = voting.Election(rules, votes)
    election.run()

    if rules["show_details"]:
        util.print_steps_election(election)
    util.pretty_print_election(election)
    if rules["to_xlsx"]:
        util.election_to_xlsx(election, rules["to_xlsx"])


if __name__ == '__main__':
    cli()
