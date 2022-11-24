"""Module for saving read records"""

ARC_FLAGS = {"A": 1 << 1, "P": 1 << 2, "C": 1 << 3, "Z": 1 << 5, "S": 1 << 6}

#    ARC_FLAG_WAIT           = 1 << 0,   /* perform sync I/O */
#    ARC_FLAG_NOWAIT         = 1 << 1,   /* perform async I/O */
#    ARC_FLAG_PREFETCH       = 1 << 2,   /* I/O is a prefetch */
#    ARC_FLAG_CACHED         = 1 << 3,   /* I/O was in cache */
#    ARC_FLAG_L2CACHE        = 1 << 4,   /* cache in L2ARC */
#    ARC_FLAG_PREDICTIVE_PREFETCH    = 1 << 5,   /* I/O from zfetch */
#    ARC_FLAG_PRESCIENT_PREFETCH = 1 << 6,   /* long min lifespan */

# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ReadRecord:
    """One read record for pool reads"""

    def __init__(self, uid, objset, dataset_name, object_id, aflags, pid, process):
        self.uid = uid
        self.objset = objset
        self.object_id = object_id
        self.dataset_name = dataset_name
        self.aflags = aflags
        self.pid = pid
        self.process = process
        self.flags = []
        # pylint: disable=consider-using-dict-items
        for flag in ARC_FLAGS:
            if (int(aflags, 16) & ARC_FLAGS[flag]) != 0:
                self.flags.append(flag)
