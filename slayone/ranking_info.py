from sortedcontainers import SortedDict

class RankingInfoDict(SortedDict):
    def __init__(self, *args, **kwargs):
        """ input lambda key: -key when using this """
        super().__init__(*args, **kwargs)

    def set_score(self, id, score):
        id_set: set = self.get(score)

        if id_set:
            id_set.add(id)
        else:
            self[score] = {id}
    
    def update_score(self, id, old_score, new_score):
        old_id_set: set = self.get(old_score)

        if old_id_set:
            old_id_set.remove(id)

            if len(old_id_set) == 0:
                del self[old_score]
        
        self.set_score(id, new_score)
    
    def remove_id(self, id, score):
        id_set: set = self[score]

        try:
            id_set.remove(id)
        except:
            print(self, "error")

        if len(id_set) == 0:
            del self[score]

    def set_all_to_zero_score(self):
        id_set: set = self.get(0)
        if id_set == None:
            id_set = set()
        
        dict_length = len(self)

        while dict_length != 0:
            score, other_id_set = self.popitem()

            if score != 0:
                id_set.update(other_id_set)

            dict_length -= 1
        
        self[0] = id_set

    def get_rank_by_score(self, score):
        return self.bisect_left(score)