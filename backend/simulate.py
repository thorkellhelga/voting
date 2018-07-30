# from voting import Election, SIMULATION_VARIATES
from rules import Rules
from math import sqrt
from random import betavariate, uniform
from copy import copy, deepcopy

import voting
import io
import json


def avg(v):
    return sum(v)/len(v)

def var(v, mean):
    return sum([(i-mean)**2 for i in v])/(len(v)-1)

def beta_params(mean, var_param):
    alpha = mean*(1/var_param**2 - 1)
    beta = alpha*(1/mean - 1)
    return alpha, beta

def beta_distribution(m_ref_votes, var_param):
    m_votes = []
    m_shares = []
    ref_totals = [sum(c) for c in m_ref_votes]
    
    for i in range(len(m_ref_votes)):
        s = 0
        m_votes.append([])
        for j in range(len(m_ref_votes[i])):
            mean_beta_distr = m_ref_votes[i][j]/ref_totals[i]
            if mean_beta_distr > 0:
                var_beta = var_param*mean_beta_distr*(1-mean_beta_distr)
                alpha, beta = beta_params(mean_beta_distr, var_param)
                share = betavariate(alpha, beta)
            else:
                share = 0
            m_votes[i].append(int(share*ref_totals[i]))
        shares = [v/sum(m_votes[i]) for v in m_votes[i]]
        m_shares.append(shares)

    return m_votes, m_shares

def beta_gen(m_ref_votes, var_param):
    while True:
        yield beta_distribution(m_ref_votes, var_param)

GENERATING_METHODS = {
    "beta": beta_gen
}

GENERATING_METHOD_NAMES = {
    "beta": "Beta distribution"
}

def error(avg, ref):
    """
    Compare average of generated votes to reference votes to test the
    quality of the simulation.
    """
    num_consts = len(avg)
    num_parties = len(avg[0])
    s = 0
    for i in range(num_consts):
        for j in range(num_parties):
            if type(ref) is list:
                s += abs(avg[i][j] - ref[i][j])
            else:
                s += abs(avg[i][j] - ref)
    return s/(num_consts*num_parties)

def dev(results, ref):
    """Calculate seat deviation of results compared to reference results."""
    d = 0
    for i in range(len(results)):
        for j in range(len(results[i])):
            d += abs(results[i][j] - ref[i][j])
    return d

def add_totals(m):
    nm = deepcopy(m)
    for i in range(len(m)):
        nm[i].append(sum(m[i]))
    totals = [sum([nm[i][j] for i in range(len(nm))]) for j in range(len(nm[0]))]
    nm.append(totals)
    return nm

def votes_to_change(election):
    ref_results = election.results
    ref_votes = election.m_votes
    votes_to_change = []
    votes = deepcopy(ref_votes)
    for c in range(len(ref_results)):
        votes_to_change.append([])
        for p in range(len(ref_results[c])):
            if ref_votes[c][p] == 0:
                votes_to_change[c].append(None)
                continue
            a = 0
            b = int(0.1*votes[c][p])
            d = 0
            while d == 0:
                votes[c][p] = ref_votes[c][p]+b
                election = voting.Election(election.rules, votes)
                results = election.run()
                d = dev(results, ref_results)
                if d == 0:
                    a = copy(b)
                    b = int(sqrt(2)*b)
            m = b-a
            x = 0
            while m > 1:
                x = int(m*sqrt(0.5) + a)
                votes[c][p] = ref_votes[c][p]+x
                election = voting.Election(election.rules, votes)
                results = election.run()
                d = dev(results, ref_results)
                if d == 0:
                    a = copy(x)
                else:
                    b = copy(x)
                m = b-a
            votes_to_change[c].append(b)
            votes[c][p] = ref_votes[c][p]

    return votes_to_change


class SimulationRules(Rules):
    def __init__(self):
        super(SimulationRules, self).__init__()
        # Simulation rules
        self["simulate"] = False
        self["simulation_count"] = 10000
        self["gen_method"] = "beta"


class Simulation:
    """Simulate a set of elections."""
    def __init__(self, rules, election, var_param=0.1):
        self.rules = rules
        self.ref_votes = add_totals(election.m_votes)
        self.ref_shares = [[v/c[-1] for v in c] for c in self.ref_votes]
        self.variate = self.rules["gen_method"]
        self.election = election
        self.var_param = var_param

    def gen_votes(self):
        """
        Generate votes similar to given votes using the given generating
        method.
        """
        self.simul_votes = []
        self.sq_simul_votes = []
        self.simul_shares = []
        self.sq_simul_shares = []
        for i in range(len(self.ref_votes)):
            self.simul_votes.append([0]*len(self.ref_votes[0]))
            self.sq_simul_votes.append([0]*len(self.ref_votes[0]))
            self.simul_shares.append([0]*len(self.ref_votes[0]))
            self.sq_simul_shares.append([0]*len(self.ref_votes[0]))
        gen = GENERATING_METHODS[self.variate]
        while True:
            votes, shares = next(gen(self.election.m_votes, self.var_param))
            for i in range(len(votes)):
                for j in range(len(votes[i])):
                    self.simul_votes[i][j] += votes[i][j]
                    self.sq_simul_votes[i][j] += votes[i][j]**2
                    self.simul_shares[i][j] += shares[i][j]
                    self.sq_simul_shares[i][j] += shares[i][j]**2
                self.simul_votes[i][-1] += sum(votes[i])
                self.sq_simul_votes[i][-1] += sum(votes[i])**2
                self.simul_shares[i][-1] += sum(shares[i])
                self.sq_simul_shares[i][-1] += sum(shares[i])**2
            total_votes = [sum([c[p] for c in votes]) for p in range(len(votes[0]))]
            total_votes.append(sum(total_votes))
            total_shares = [t/total_votes[-1] for t in total_votes]
            for i in range(len(total_votes)):
                self.simul_votes[-1][i] += total_votes[i]
                self.sq_simul_votes[-1][i] += total_votes[i]**2
                self.simul_shares[-1][i] += total_shares[i]
                self.sq_simul_shares[-1][i] += total_shares[i]**2
            yield votes, shares

    def test_generated(self):
        """Analysis of generated votes."""
        n = self.rules["simulation_count"]
        self.avg_simul_votes = [[v/n for v in c] for c in self.simul_votes]
        self.avg_simul_shares = [[s/n for s in c] for c in self.simul_shares]
        avg_simul_votes = []
        avg_simul_shares = []
        var_simul_votes = []
        var_simul_shares = []
        var_beta_distr = []

        for i in range(len(self.ref_votes)):
            var_simul_votes.append([])
            var_simul_shares.append([])
            var_beta_distr.append([])
            for j in range(len(self.ref_votes[i])):
                variance_votes = (self.sq_simul_votes[i][j]
                                    -self.simul_votes[i][j]**2/n) / (n-1)
                variance_shares = (self.sq_simul_shares[i][j]
                                    -self.simul_shares[i][j]**2/n) / (n-1)
                var_simul_votes[i].append(variance_votes)
                var_simul_shares[i].append(variance_shares)

                var_beta_distr[i].append(self.var_param
                                        *self.ref_shares[i][j]
                                        *(self.ref_shares[i][j]-1))

        self.var_simul_votes = var_simul_votes
        self.var_simul_shares = var_simul_shares
        self.error_avg_simul_shares = error(self.avg_simul_shares,
                                            self.ref_shares)
        self.error_var_simul_shares = error(var_simul_shares, var_beta_distr)


    def method_analysis(self, ref_rules, votes, results, entropy):
        """Various tests to determine the quality of the given method."""
        opt_rules = ref_rules["opt"]
        law_rules = ref_rules["law"]
        ind_const_rules = ref_rules["ind_const"]
        one_country_rules = ref_rules["one_country"]
        tot_eq_one_country_rules = ref_rules["tot_eq_one_country"]
        opt_election = voting.Election(opt_rules, votes)
        opt_results = opt_election.run()
        opt_entropy = opt_election.entropy()
        entropy_ratio = entropy/opt_entropy
        self.entropy_ratio += entropy_ratio
        self.sq_entropy_ratio += entropy_ratio**2
        dev_opt = dev(results, opt_results)
        self.dev_opt += dev_opt
        self.sq_dev_opt += dev_opt**2
        law_election = voting.Election(law_rules, votes)
        law_results = law_election.run()
        dev_law = dev(results, law_results)
        self.dev_law += dev_law
        self.sq_dev_law += dev_law**2
        ind_const_election = voting.Election(ind_const_rules, votes)
        ind_const_results = ind_const_election.run()
        dev_ind_const = dev(results, ind_const_results)
        self.dev_ind_const += dev_ind_const
        self.sq_dev_ind_const += dev_ind_const**2
        v_votes = [[sum([c[p] for c in votes]) for p in range(len(votes[0]))]]
        one_country_election = voting.Election(one_country_rules, v_votes)
        one_country_results = one_country_election.run()
        v_results = [[sum([c[p] for c in results]) for p in range(len(results[0]))]]
        dev_one_country = dev(v_results, one_country_results)
        self.dev_one_country += dev_one_country
        self.sq_dev_one_country += dev_one_country**2
        tot_eq_one_country_election = voting.Election(tot_eq_one_country_rules, v_votes)
        tot_eq_one_country_results = tot_eq_one_country_election.run()
        dev_tot_eq_one_country = dev(v_results, tot_eq_one_country_results)
        self.dev_tot_eq_one_country += dev_tot_eq_one_country
        self.sq_dev_tot_eq_one_country += dev_tot_eq_one_country**2

        bi_seat_shares = deepcopy(votes)
        const_mult = [1]*len(bi_seat_shares)
        party_mult = [1]*len(bi_seat_shares[0])
        seats_party_opt = [sum([c[p] for c in opt_results]) 
                            for p in range(len(opt_results[0]))]
        error = 1
        while round(error, 5) != 0.0:
            const_mult = [self.seats_total_const[c]/sum(bi_seat_shares[c])
                            for c in range(len(self.seats_total_const))]
            s = [sum([c[p] for c in bi_seat_shares]) for p in range(len(bi_seat_shares[0]))]
            party_mult = [seats_party_opt[p]/s[p] if s[p] != 0 else 1
                            for p in range(len(seats_party_opt))]
            for c in range(len(bi_seat_shares)):
                for p in range(len(bi_seat_shares[c])):
                    r = uniform(0.0, 1.0)
                    bi_seat_shares[c][p] *= 1 - r + r*const_mult[c]*party_mult[p]
            error = sum([abs(1-cm) for cm in const_mult]) + sum([abs(1-pm) for pm in party_mult])

        try:
            assert(all([sum([c[p] for c in bi_seat_shares]) == seats_party_opt[p]
                        for p in range(len(seats_party_opt))]))
        except AssertionError:
            pass
        try:
            assert(all([sum(bi_seat_shares[c]) == self.seats_total_const[c]
                        for c in range(len(self.seats_total_const))]))
        except AssertionError:
            pass

        total_seats = sum([sum(c) for c in results])
        lh = sum([sum([abs(bi_seat_shares[c][p]-results[c][p])
                    for p in range(len(results[c]))])
                    for c in range(len(results))]) / (2*total_seats)
        self.lh += lh
        self.sq_lh += lh**2
        scale = 1
        stl = sum([sum([(bi_seat_shares[c][p]-results[c][p])**2/bi_seat_shares[c][p]
                    if bi_seat_shares[c][p] != 0 else 0
                    for p in range(len(results[c]))])
                    for c in range(len(results))]) * scale
        self.stl += stl
        self.sq_stl += stl**2
        dh_min = min([bi_seat_shares[c][p]/results[c][p]
                    if results[c][p] != 0 else 0
                    for p in range(len(results[c]))
                    for c in range(len(results))])
        self.dh_min += dh_min
        self.sq_dh_min += dh_min**2
        dh_sum = sum([max(0, bi_seat_shares[c][p]-results[c][p])/bi_seat_shares[c][p] if bi_seat_shares[c][p] != 0 else 0
                        for p in range(len(results[c]))
                        for c in range(len(results))])
        self.dh_sum += dh_sum
        self.sq_dh_sum += dh_sum**2

    def analysis(self):
        n = self.rules["simulation_count"]
        self.avg_const_seats = [[s/n for s in c] for c in self.const_seats]
        self.var_const_seats = []
        self.avg_adj_seats = [[s/n for s in c] for c in self.adj_seats]
        self.var_adj_seats = []
        self.avg_total_seats = [[s/n for s in c] for c in self.total_seats]
        self.var_total_seats = []
        self.avg_seat_shares = [[s/n for s in c] for c in self.seat_shares]
        self.var_seat_shares = []
        for i in range(len(self.ref_votes)):
            self.var_const_seats.append([])
            self.var_adj_seats.append([])
            self.var_total_seats.append([])
            self.var_seat_shares.append([])
            for j in range(len(self.ref_votes[i])):
                variance = (self.sq_const_seats[i][j] - self.const_seats[i][j]**2/n) / (n-1)
                self.var_const_seats[i].append(variance)
                variance = (self.sq_adj_seats[i][j] - self.adj_seats[i][j]**2/n) / (n-1)
                self.var_adj_seats[i].append(variance)
                variance = (self.sq_total_seats[i][j] - self.total_seats[i][j]**2/n) / (n-1)
                self.var_total_seats[i].append(variance)
                variance = abs(self.sq_seat_shares[i][j] - self.seat_shares[i][j]**2/n) / (n-1)
                self.var_seat_shares[i].append(variance)

        self.avg_entropy = self.entropy/n
        self.var_entropy = (self.sq_entropy - self.entropy**2/n) / (n-1)
        self.avg_entropy_ratio = self.entropy_ratio/n
        self.var_entropy_ratio = (self.sq_entropy_ratio - self.entropy_ratio**2/n) / (n-1)
        self.avg_dev_opt = self.dev_opt/n
        self.var_dev_opt = (self.sq_dev_opt - self.dev_opt**2/n) / (n-1)
        self.avg_dev_law = self.dev_law/n
        self.var_dev_law = (self.sq_dev_law - self.dev_law**2/n) / (n-1)
        self.avg_dev_ind_const = self.dev_ind_const/n
        self.var_dev_ind_const = (self.sq_dev_ind_const - self.dev_ind_const**2/n) / (n-1)
        self.avg_dev_one_country = self.dev_one_country/n
        self.var_dev_one_country = (self.sq_dev_one_country - self.dev_one_country**2/n) / (n-1)
        self.avg_dev_tot_eq_one_country = self.dev_tot_eq_one_country/n
        self.var_dev_tot_eq_one_country = (self.sq_dev_tot_eq_one_country - self.dev_tot_eq_one_country**2/n) / (n-1)
        self.avg_lh = self.lh/n
        self.var_lh = (self.sq_lh - self.lh**2/n) / (n-1)
        self.avg_stl = self.stl/n
        self.var_stl = (self.sq_stl - self.stl**2/n) / (n-1)
        self.avg_dh_min = self.dh_min/n
        self.var_dh_min = (self.sq_dh_min - self.dh_min**2/n) / (n-1)
        self.avg_dh_sum = self.dh_sum/n
        self.var_dh_sum = (self.sq_dh_sum - self.dh_sum**2/n) / (n-1)

    def simulate(self):
        """Simulate many elections."""
        gen = self.gen_votes()
        e_rules = self.election.rules
        ref_rules = sim_ref_rules(e_rules)
        r = self.election.run()
        self.const_seats, self.sq_const_seats = [], []
        self.adj_seats, self.sq_adj_seats = [], []
        self.total_seats, self.sq_total_seats = [], []
        self.seat_shares, self.sq_seat_shares = [], []
        for i in range(len(self.ref_votes)):
            self.const_seats.append([0]*(len(self.ref_votes[i])))
            self.sq_const_seats.append([0]*(len(self.ref_votes[i])))
            self.adj_seats.append([0]*(len(self.ref_votes[i])))
            self.sq_adj_seats.append([0]*(len(self.ref_votes[i])))
            self.total_seats.append([0]*(len(self.ref_votes[i])))
            self.sq_total_seats.append([0]*(len(self.ref_votes[i])))
            self.seat_shares.append([0]*(len(self.ref_votes[i])))
            self.sq_seat_shares.append([0]*(len(self.ref_votes[i])))
        self.entropy, self.sq_entropy = 0, 0
        self.entropy_ratio, self.sq_entropy_ratio = 0, 0
        self.dev_opt, self.sq_dev_opt = 0, 0
        self.dev_law, self.sq_dev_law = 0, 0
        self.dev_ind_const, self.sq_dev_ind_const = 0, 0
        self.dev_one_country, self.sq_dev_one_country = 0, 0
        self.dev_tot_eq_one_country, self.sq_dev_tot_eq_one_country = 0, 0
        self.lh, self.sq_lh = 0, 0
        self.stl, self.sq_stl = 0, 0
        self.dh_min, self.sq_dh_min = 0, 0
        self.dh_sum, self.sq_dh_sum = 0, 0
        self.seats_total_const = copy(self.election.v_total_seats)
        for i in range(self.rules["simulation_count"]):
            votes, shares = next(gen)
            election = voting.Election(e_rules, votes)
            results = election.run()
            const_seats_alloc = add_totals(election.const_seats_alloc)
            total_seats_alloc = add_totals(results)
            for c in range(len(self.total_seats)):
                for p in range(len(self.total_seats[c])):
                    self.const_seats[c][p] += const_seats_alloc[c][p]
                    self.sq_const_seats[c][p] += const_seats_alloc[c][p]**2
                    adj = total_seats_alloc[c][p]-const_seats_alloc[c][p]
                    self.adj_seats[c][p] += adj
                    self.sq_adj_seats[c][p] += adj**2
                    self.total_seats[c][p] += total_seats_alloc[c][p]
                    self.sq_total_seats[c][p] += total_seats_alloc[c][p]**2
                    sh = total_seats_alloc[c][p]/total_seats_alloc[c][-1]
                    self.seat_shares[c][p] += sh
                    self.sq_seat_shares[c][p] += sh**2
            entropy = election.entropy()
            self.entropy += entropy
            self.sq_entropy += entropy**2
            self.method_analysis(ref_rules, votes, results, entropy)
        self.analysis()
        self.test_generated()

        self.votes_to_change = votes_to_change(self.election)


    def get_results_dict(self):
        return {
            "methods": [self.election.rules["adjustment_method"]],
            "measures": ["entropy", "entropy_ratio", "dev_opt", "dev_law", "dev_ind_const", "dev_one_country", "dev_tot_eq_one_country",
                "lh", "stl", "dh_min", "dh_sum"],
            "numbers": [round(n,2) for n in [self.avg_entropy, self.avg_entropy_ratio, self.avg_dev_opt, self.avg_dev_law, self.avg_dev_ind_const,
                self.avg_dev_one_country, self.avg_dev_tot_eq_one_country, self.avg_lh, self.avg_stl, self.avg_dh_min, self.avg_dh_sum]]
        }


def sim_ref_rules(rs):

    opt_rs = voting.ElectionRules()
    law_rs = voting.ElectionRules()
    ind_const_rs = voting.ElectionRules()
    one_country_rs = voting.ElectionRules()
    tot_eq_one_country_rs = voting.ElectionRules()

    opt_rs.update(rs)
    opt_rs["adjustment_method"] = "alternating-scaling"
    law_rs["adjustment_method"] = "icelandic-law"
    law_rs["primary_divider"] = "dhondt"
    law_rs["adjustment_divider"] = "dhondt"
    law_rs["adjustment_threshold"] = 0.05
    law_rs["constituency_seats"] = rs["constituency_seats"]
    law_rs["constituency_adjustment_seats"] = rs["constituency_adjustment_seats"]
    law_rs["constituency_names"] = rs["constituency_names"]
    law_rs["parties"] = rs["parties"]
    ind_const_rs.update(rs)
    ind_const_rs["constituency_seats"] = copy(rs["constituency_seats"])
    ind_const_rs["constituency_adjustment_seats"] = []
    for i in range(len(rs["constituency_seats"])):
        ind_const_rs["constituency_seats"][i] += rs["constituency_adjustment_seats"][i]
        ind_const_rs["constituency_adjustment_seats"].append(0)
    one_country_rs.update(rs)
    one_country_rs["constituency_seats"] = [sum(rs["constituency_seats"])]
    one_country_rs["constituency_adjustment_seats"] = [sum(rs["constituency_adjustment_seats"])]
    one_country_rs["constituency_names"] = ["All"]
    tot_eq_one_country_rs.update(one_country_rs)
    tot_eq_one_country_rs["constituency_seats"] = [0]
    tot_eq_one_country_rs["constituency_adjustment_seats"] = [one_country_rs["constituency_seats"][0]
                        + one_country_rs["constituency_adjustment_seats"][0]]

    ref = {"opt": opt_rs,
            "law": law_rs,
            "ind_const": ind_const_rs,
            "one_country": one_country_rs, 
            "tot_eq_one_country": tot_eq_one_country_rs}

    return ref

def run_script_simulation(rules):
    srs = SimulationRules()
    srs.update(rules["simulation_rules"])

    rs = voting.ElectionRules()
    rs.update(rules["election_rules"])

    if not "ref_votes" in rules:
        return {"error": "No reference votes supplied."}

    election = voting.Election(rs, rules["ref_votes"])

    sim = Simulation(srs, election)
    sim.simulate()

    return sim
