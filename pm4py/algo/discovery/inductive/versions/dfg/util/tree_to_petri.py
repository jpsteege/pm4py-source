from pm4py.objects import petri
from pm4py.objects.petri.petrinet import PetriNet
from pm4py.algo.discovery.inductive.versions.dfg.util.petri_el_add import get_new_place, get_new_hidden_trans, \
    get_transition
from pm4py.algo.discovery.inductive.versions.dfg.util.check_skip_trans import verify_skip_transition_necessity, verify_skip_for_parallel_cut

def form_petrinet(tree, recDepth, counts, net, initial_marking, final_marking, must_add_initial_place=False,
                  must_add_final_place=False, initial_connect_to=None, final_connect_to=None, must_add_skip=False,
                  must_add_loop=False):
    """
    Form a Petri net from the current tree structure

    Parameters
    -----------
    tree
        Current recursion subtree
    recDepth
        Current recursion depth
    counts
        Count object
    net
        Petri net object
    initial_marking
        Initial marking object
    final_marking
        Final marking object
    must_add_initial_place
        When recursive calls are done, tells to add a new place (from which the subtree starts)
    must_add_final_place
        When recursive calls are done, tells to add a new place (into which the subtree goes)
    initial_connect_to
        Initial element (place/transition) to which we should connect the subtree
    final_connect_to
        Final element (place/transition) to which we should connect the subtree
    must_add_skip
        Must add skip transition
    must_add_loop
        Must add loop transition

    Returns
    ----------
    net
        Petri net object
    initial_marking
        Initial marking object
    final_marking
        Final marking object
    lastAddedPlace
        lastAddedPlace
    """
    last_added_place = None
    initial_place = None
    final_place = None
    if recDepth == 0:
        source = get_new_place(counts)
        initial_connect_to = source
        initial_place = source
        net.places.add(source)
        sink = get_new_place(counts)
        final_connect_to = sink
        net.places.add(sink)
        last_added_place = sink
    elif recDepth > 0:
        if must_add_initial_place or type(initial_connect_to) is PetriNet.Transition:
            initial_place = get_new_place(counts)
            net.places.add(initial_place)
            petri.utils.add_arc_from_to(initial_connect_to, initial_place, net)
        else:
            initial_place = initial_connect_to
        if must_add_final_place or type(final_connect_to) is PetriNet.Transition:
            final_place = get_new_place(counts)
            net.places.add(final_place)
            petri.utils.add_arc_from_to(final_place, final_connect_to, net)
        else:
            final_place = final_connect_to
        if counts.num_places == 2 and len(tree.activities) > 1:
            initial_trans = get_new_hidden_trans(counts, type="tau")
            net.transitions.add(initial_trans)
            new_place = get_new_place(counts)
            net.places.add(new_place)
            petri.utils.add_arc_from_to(initial_connect_to, initial_trans, net)
            petri.utils.add_arc_from_to(initial_trans, new_place, net)
            initial_place = new_place

    if tree.detected_cut == "base_concurrent" or tree.detected_cut == "flower":
        if final_connect_to is None or type(final_connect_to) is PetriNet.Transition:
            if final_place is not None:
                last_added_place = final_place
            else:
                last_added_place = get_new_place(counts)
                net.places.add(last_added_place)
        else:
            last_added_place = final_connect_to

        prev_no_visible_trans = counts.num_visible_trans

        for act in tree.activities:
            trans = get_transition(counts, act)
            net.transitions.add(trans)
            petri.utils.add_arc_from_to(initial_place, trans, net)
            petri.utils.add_arc_from_to(trans, last_added_place, net)



        if verify_skip_transition_necessity(must_add_skip, tree.initial_dfg, tree.activities) and not initial_connect_to.name == "p_1" and prev_no_visible_trans > 0:
            # add skip transition
            skipTrans = get_new_hidden_trans(counts, type="skip")
            net.transitions.add(skipTrans)
            petri.utils.add_arc_from_to(initial_place, skipTrans, net)
            petri.utils.add_arc_from_to(skipTrans, last_added_place, net)

    # iterate over childs
    if tree.detected_cut == "sequential" or tree.detected_cut == "loopCut":

        mAddSkip = False
        mAddLoop = False
        if tree.detected_cut == "loopCut":
            mAddSkip = True
            mAddLoop = True

        net, initial_marking, final_marking, last_added_place, counts = form_petrinet(tree.children[0], recDepth + 1,
                                                                                      counts, net, initial_marking,
                                                                                      final_marking,
                                                                                      initial_connect_to=initial_place,
                                                                                      must_add_skip=verify_skip_transition_necessity(
                                                                                          mAddSkip,
                                                                                          tree.initial_dfg,
                                                                                          tree.activities),
                                                                                      must_add_loop=mAddLoop)
        net, initial_marking, final_marking, last_added_place, counts = form_petrinet(tree.children[1], recDepth + 1,
                                                                                      counts, net,
                                                                                      initial_marking,
                                                                                      final_marking,
                                                                                      initial_connect_to=last_added_place,
                                                                                      final_connect_to=final_place,
                                                                                      must_add_skip=verify_skip_transition_necessity(
                                                                                          mAddSkip,
                                                                                          tree.initial_dfg,
                                                                                          tree.activities),
                                                                                      must_add_loop=mAddLoop)
    elif tree.detected_cut == "parallel":
        mAddLoop = False

        if final_place is None:
            final_place = get_new_place(counts)
            net.places.add(final_place)

        mAddSkip = verify_skip_for_parallel_cut(tree.dfg, tree.children)

        parallelSplit = get_new_hidden_trans(counts, "tauSplit")
        net.transitions.add(parallelSplit)
        petri.utils.add_arc_from_to(initial_place, parallelSplit, net)

        parallelJoin = get_new_hidden_trans(counts, "tauJoin")
        net.transitions.add(parallelJoin)
        petri.utils.add_arc_from_to(parallelJoin, final_place, net)

        for child in tree.children:
            mAddSkipFinal = verify_skip_transition_necessity(mAddSkip, tree.dfg, tree.activities)

            net, initial_marking, final_marking, last_added_place, counts = form_petrinet(child, recDepth + 1, counts,
                                                                                          net, initial_marking,
                                                                                          final_marking,
                                                                                          must_add_initial_place=True,
                                                                                          must_add_final_place=True,
                                                                                          initial_connect_to=parallelSplit,
                                                                                          final_connect_to=parallelJoin,
                                                                                          must_add_skip=mAddSkipFinal,
                                                                                          must_add_loop=mAddLoop)

        last_added_place = final_place

    elif tree.detected_cut == "concurrent":
        mAddSkip = False
        mAddLoop = False

        if final_place is None:
            final_place = get_new_place(counts)
            net.places.add(final_place)

        for child in tree.children:
            net, initial_marking, final_marking, last_added_place, counts = form_petrinet(child, recDepth + 1, counts,
                                                                                          net, initial_marking,
                                                                                          final_marking,
                                                                                          initial_connect_to=initial_place,
                                                                                          final_connect_to=final_place,
                                                                                          must_add_skip=verify_skip_transition_necessity(
                                                                                              mAddSkip,
                                                                                              tree.initial_dfg,
                                                                                              tree.activities),
                                                                                          must_add_loop=mAddLoop)

        last_added_place = final_place

    if tree.detected_cut == "flower" or tree.detected_cut == "sequential" or tree.detected_cut == "loopCut" or tree.detected_cut == "base_concurrent" or tree.detected_cut == "parallel" or tree.detected_cut == "concurrent":
        if must_add_skip:
            if not (initial_place.name in counts.dict_skips and last_added_place.name in counts.dict_skips[
                initial_place.name]):
                skipTrans = get_new_hidden_trans(counts, type="skip")
                net.transitions.add(skipTrans)
                petri.utils.add_arc_from_to(initial_place, skipTrans, net)
                petri.utils.add_arc_from_to(skipTrans, last_added_place, net)

                if not initial_place.name in counts.dict_skips:
                    counts.dict_skips[initial_place.name] = []

                counts.dict_skips[initial_place.name].append(last_added_place.name)

        if tree.detected_cut == "flower" or must_add_loop:
            if not (initial_place.name in counts.dict_loops and last_added_place.name in counts.dict_loops[
                initial_place.name]):
                loopTrans = get_new_hidden_trans(counts, type="loop")
                net.transitions.add(loopTrans)
                petri.utils.add_arc_from_to(last_added_place, loopTrans, net)
                petri.utils.add_arc_from_to(loopTrans, initial_place, net)

                if not initial_place.name in counts.dict_loops:
                    counts.dict_loops[initial_place.name] = []

                counts.dict_loops[initial_place.name].append(last_added_place.name)

    if recDepth == 0:
        if len(sink.out_arcs) == 0 and len(sink.in_arcs) == 0:
            net.places.remove(sink)
            sink = last_added_place

        if len(sink.out_arcs) > 0:
            newSink = get_new_place(counts)
            net.places.add(newSink)
            newHidden = get_new_hidden_trans(counts, type="tau")
            net.transitions.add(newHidden)
            petri.utils.add_arc_from_to(sink, newHidden, net)
            petri.utils.add_arc_from_to(newHidden, newSink, net)
            sink = newSink

        if len(source.in_arcs) > 0:
            newSource = get_new_place(counts)
            net.places.add(newSource)
            newHidden = get_new_hidden_trans(counts, type="tau")
            net.transitions.add(newHidden)
            petri.utils.add_arc_from_to(newSource, newHidden, net)
            petri.utils.add_arc_from_to(newHidden, source, net)
            source = newSource

        source.name = "source"
        sink.name = "sink"
        initial_marking[source] = 1
        final_marking[sink] = 1

    return net, initial_marking, final_marking, last_added_place, counts