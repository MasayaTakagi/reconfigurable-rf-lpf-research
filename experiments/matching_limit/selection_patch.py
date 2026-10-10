"""Balanced selection across internal-node count and area-cost bins."""
from collections import defaultdict
from topology_selection import area_thirds,has_signal_path,has_unproductive_internal_leaf,topology_signature

def select_node_balanced(graphs,per_node_bin,require_shunt=False):
    """Each populated (internal-node count, area bin) gets its own budget."""
    if per_node_bin<0:raise ValueError('Negative budget')
    cells=defaultdict(list)
    for g in graphs:
        n,edges=g
        if not has_signal_path(g) or has_unproductive_internal_leaf(g):continue
        if require_shunt and not any(0 in (a,b) for a,b,_ in edges):continue
        area=area_thirds(g)
        if area>18 or sum(t=='PCB_L' for _,_,t in edges)>3:continue
        b=0 if area<=6 else 1 if area<=12 else 2
        cells[(n-3,b)].append(g)
    chosen=[]
    for cell in sorted(cells):
        families=defaultdict(list)
        for g in cells[cell]:families[topology_signature(g)].append(g)
        for group in families.values():group.sort(key=str)
        keys=sorted(families,key=str)
        selected_in_cell=0
        while keys and selected_in_cell<per_node_bin:
            for key in list(keys):
                if selected_in_cell>=per_node_bin:break
                chosen.append((cell,families[key].pop(0)))
                selected_in_cell+=1
                if not families[key]:keys.remove(key)
    return chosen,{f'n{k[0]}_P{k[1]+2}':len(v) for k,v in sorted(cells.items())}
