"""Transfer-power insertion loss; input is a power ratio, not S21 magnitude."""
import math

def insertion_loss_db(p_load,p_available):
    if p_available<=0 or p_load<=0:
        raise ValueError('Power must be positive')
    return -10*math.log10(p_load/p_available)
