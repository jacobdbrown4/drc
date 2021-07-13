import spydrnet as sdn
from spydrnet.uniquify import uniquify
from spydrnet.util import selection
from spydrnet_shrec import insert_organs, apply_nmr
from spydrnet_shrec.analysis.find_voter_insertion_points import find_voter_insertion_points
from spydrnet_shrec.transformation.replication.organ import XilinxTMRVoter
from spydrnet_shrec.transformation.replication.uniquify_nmr_property import uniquify_nmr_property
import time
def get_modified_netlist(example_name):

    netlist = sdn.load_example_netlist_by_name(example_name)
    # netlist = sdn.parse("counters128.edf")

    uniquify(netlist)
    sdn.compose(netlist,'counters128.edf')

    # hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x: x.item.reference.is_leaf() is True))
    # instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    # hports_to_replicate = list(netlist.get_hports())
    # ports_to_replicate = list(x.item for x in hports_to_replicate)
    hinstances_to_replicate = list(netlist.get_hinstances(recursive=True, filter=lambda x:(x.item.reference.is_leaf() and 'OBUF' not in x.item.name.upper() and 'OUTBUF' not in x.item.name.upper() and 'segment' not in x.item.name and 'anode' not in x.item.name)is True))
    instances_to_replicate = list(x.item for x in hinstances_to_replicate)
    hports_to_replicate = list(netlist.get_hports(filter = lambda x: (x.item.direction is sdn.IN and 'clk' not in x.item.name) is True))
    ports_to_replicate = list(x.item for x in hports_to_replicate)

    insertion_points = find_voter_insertion_points(netlist, [*hinstances_to_replicate, *hports_to_replicate], {'FDRE', 'FDSE', 'FDPE', 'FDCE'})
    replicas = apply_nmr([*instances_to_replicate, *ports_to_replicate], 3, name_suffix='TMR', rename_original=True)
    voters = insert_organs(replicas, insertion_points, XilinxTMRVoter(), 'VOTER')
    # uniquify_nmr_property(replicas, {'HBLKNM', 'HLUTNM', 'SOFT_HLUTNM'}, "TMR")
    netlist.compose(example_name+"_modified.edf")

    # for instance in netlist.get_instances(filter = lambda x : ('VOTER[63]' in x.name) is True):
    #     print(instance.name)
    #     out_pin = next(instance.get_pins(selection= selection.Selection.OUTcounters128E,filter=lambda x: x.inner_pin.port.direction is sdn.OUT))
    #     print(list(x.instance.name for x in out_pin.wire.get_pins(selection=selection.Selection.OUTcounters128E)))
    # # for point in insertion_points:
    # #     print(point.instance.name,' of ',point.instance.parent.name)
    # # print('\n\n')

# get_modified_netlist('counters128')

# import cProfile
# import re
from design_rule_check import check_design
tparse_0 = time.time()
netlist1 = sdn.parse("counters128.edf")
tparse_1 = time.time()
print("TIME TO PARSE ORIGINAL:",tparse_1-tparse_0)
tparse_2 = time.time()
netlist2 = sdn.parse("counters128_modified.edf")
tparse_3 = time.time()
print("TIME TO PARSE MODIFIED:",tparse_3-tparse_2)
check_design(netlist1,netlist2,'TMR','VOTER')
# cProfile.run("re.compile(check_design(netlist1,netlist2,'TMR','VOTER'))")

# print(sdn.example_netlist_names)
# netlist = sdn.parse("counters128_modified.edf")

# print(len([]))
