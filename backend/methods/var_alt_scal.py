from apportion import apportion1d
from copy import deepcopy


def var_alt_scal(m_votes, v_const_seats, v_party_seats,
                        m_prior_allocations, divisor_gen, threshold, **kwargs):
    """
    # Implementation of the Alternating-Scaling algorithm.

    Inputs:
        - m_votes: A matrix of votes (rows: constituencies, columns:
          parties)
        - v_const_seats: A vector of total seats in each constituency
        - v_party_seats: A vector of seats allocated to parties
        - m_prior_allocations: A matrix of where parties have previously gotten
          seats
        - divisor_gen: A generator function generating divisors, e.g. d'Hondt
        - threshold: A cutoff threshold for participation.
    """
    m_allocations = deepcopy(m_prior_allocations)

    def const_step(v_votes, const_id, v_const_multipliers, v_party_multipliers):
        num_total_seats = v_const_seats[const_id]
        cm = const_multiplier = v_const_multipliers[const_id]
        # See IV.3.5 in paper:
        v_scaled_votes = [a/(b*cm) if b*cm != 0 else 0
                          for a, b in zip(v_votes, v_party_multipliers)]

        v_priors = m_allocations[const_id]

        alloc, div = apportion1d(v_scaled_votes, num_total_seats,
                                 v_priors, divisor_gen)

        # See IV.3.9 in paper:
        minval = div[2] # apportion1d gives us the last used value, which is min
        maxval = max([float(a)/b for a, b in zip(v_scaled_votes, div[0])])
        const_multiplier = (minval+maxval)/2

        return const_multiplier, alloc

    def party_step(v_votes, party_id, v_const_multipliers, v_party_multipliers):
        num_total_seats = v_party_seats[party_id]
        pm = party_multiplier = v_party_multipliers[party_id]
        
        v_scaled_votes = [a/(b*pm) if b != 0 else 0
                          for a, b in zip(v_votes, v_const_multipliers)]

        v_priors = [m_allocations[x][party_id]
                    for x in range(len(m_allocations))]

        alloc, div = apportion1d(v_scaled_votes, num_total_seats, v_priors,
                                 divisor_gen)

        minval = div[2]
        maxval = max([float(a)/b for a, b in zip(v_scaled_votes, div[0])])
        party_multiplier = (minval+maxval)/2

        return party_multiplier, alloc

    num_constituencies = len(m_votes)
    num_parties = len(m_votes[0])
    const_multipliers = [1] * num_constituencies
    party_multipliers = [1] * num_parties
    step = 0

    while step < 200:
        step += 1
        if step % 2 == 1:
            # Constituency step:
            muls = []
            const_allocs = []
            for c in range(num_constituencies):
                mul, alloc = const_step(m_votes[c], c, const_multipliers,
                                        party_multipliers)
                const_multipliers[c] *= mul
                muls.append(mul)
                const_allocs.append(alloc)
        else:
            # Party step:
            muls = []
            party_allocs = []
            for p in range(num_parties):
                vp = [v[p] for v in m_votes]
                mul, alloc = party_step(vp, p, const_multipliers, party_multipliers)
                party_multipliers[p] *= mul
                muls.append(mul)
                party_allocs.append(alloc)

        # Stop when constituency step and party step give the same result
        done = step != 1 and all([const_allocs[i][j] == party_allocs[j][i]
                    for i in range(len(const_allocs))
                    for j in range(len(party_allocs))])
        if done:
            break

    # Finally, use party_multipliers and const_multipliers to arrive at
    #  final apportionment:
    results = []
    for c in range(num_constituencies):
        num_total_seats = v_const_seats[c]
        cm = const_multipliers[c]
        v_scaled_votes = [a/(b*cm) if b*cm != 0 else 0
                          for a, b in zip(m_votes[c], party_multipliers)]
        v_priors = m_allocations[c]
        alloc, _ = apportion1d(v_scaled_votes, num_total_seats,
                                 v_priors, divisor_gen)
        results.append(alloc)

    return results, None
