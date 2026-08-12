"""Class that handles the queue for connecting to a party"""
import bascenev1 as bs
import babase as ba
from dataclasses import dataclass
from .party_queue_actor import PartyQueueActor

@dataclass
class QueuePlayer:
    """A player in the queue."""
    name: str
    id: str
    dist: float
    acc_id: str

class PartyQueueHandler:
    def __del__(self):
        self._done = True
        self._clear_actor()
    
    def _clear_actor(self):
        # just clear its ref for now;
        # the actor can die by itself
        self._actor._delegate = None
        self._actor = None
    
    def _update_our_actor(self):
        # if our actor is a class, but it doesn't exist,
        # we assume a new session killed it, so let's tell it to recreate itself
        if not self._actor:
            return
        if not self._actor.exists():
            self._actor._recreate()
        # update either way
        self._actor.update()
        
    def __init__(self, party_data: dict):
        self._done = False
        # get data that we got handed
        self._party_address = party_data.get('address')
        self._party_port = party_data.get('port')
        self._party_name = party_data.get('name')
        self._queue_id = party_data.get('queue_id')
        self._party_size = party_data.get('size')
        self._other_queue_guys = []
        self._connection_attempts = 0
        self._connection_attempt_limit = 10
        self._connecting = False
        self._state = None
        self._actor = PartyQueueActor(delegate=self)
        # get started
        self._check_if_full()
        self._check_for_connection()
        self._update_our_actor()
    
    def _update_queue(self, response: dict):
        self._other_queue_guys.clear()
        for (
            enemy_id,
            enemy_distance,
            enemy_account_id,
            enemy_name,
        ) in response['e']:
            self._other_queue_guys.append(
                QueuePlayer(
                    name=enemy_name,
                    id=enemy_id,
                    dist=enemy_distance,
                    acc_id=enemy_account_id,
                )
            )
        self._update_our_actor()
    
    def _check_if_full(self):
        if (
            self._party_size[0] 
            >= self._party_size[1]
        ):
            self._party_full = True
        else:
            self._party_full = False
        self._state = 'party_full'
        self._update_our_actor()
    
    def on_update_response(self, response: dict) -> None:
        if self._done:
            return
        # party full
        if self._party_full:
            ba.apptimer(5, self._check_for_connection)
        # allowed to connect
        elif response.get('c', False):
            self._attempt_connection()
        else:
            self._state = 'party_reject'
            ba.apptimer(5, self._check_for_connection)
        self._update_queue(response)
        self._update_our_actor()
    
    def _on_public_party_query_result(self, response: dict):
        if not response:
            return
        if self._done:
            return
        parties_in = response['l']
        for party in parties_in:
            addr = party['a'] # address
            port = party['p'] # port
            name = party['n'] # name
            size = (party['s'], party['sm']) # size, size max
            same_party = False
            # if we've got a match, update info
            # (good if the host changes settings midway)
            if (
                addr == self._party_address
                and port == self._party_port
            ):
                same_party = True
            if same_party:
                self._party_name = name
                self._party_address = addr
                self._party_port = port
                self._party_size = size
        self._check_if_full()
        self._update_our_actor()
    
    def _check_for_connection(self):
        if self._done:
            return
        plus = ba.app.plus
        # ask master server for some info
        # (queue status, and list of public parties)
        plus.add_v1_account_transaction(
            {
                'type': 'PUBLIC_PARTY_QUERY',
                'proto': bs.protocol_version(),
                'lang': ba.app.lang.language,
            },
            callback=ba.WeakCallPartial(
                self._on_public_party_query_result
            ),
        )
        plus.add_v1_account_transaction(
            {'type': 'PARTY_QUEUE_QUERY', 'q': self._queue_id},
            callback=ba.WeakCallPartial(self.on_update_response),
        )
        plus.run_v1_account_transactions()

    def die(self):
        # releasing this reference will
        # tell this class to del, so do so
        ba.app._party_queue_handler = None
    
    def _attempt_connection(self):
        # if we connected or already are done, we
        # do another check if we're connected, so we
        # make sure we're dead normally
        if self._done or bs.get_connection_to_host_info_2():
            ba.apptimer(1, self._check_connected)
            return
        self._state = 'connecting'
        # ok then lets connect to the party
        # (not instant... so delay check)
        self._connecting = True
        bs.connect_to_party(
            self._party_address, 
            self._party_port,
            print_progress=False,
        )
        self._update_our_actor()
        ba.apptimer(1, self._check_connected)
    
    def _check_connected(self):
        if self._done:
            return
        # if it's done, we can die peacefully now
        if bs.get_connection_to_host_info_2():
            self._state = 'connected'
            self.die()
            return
        # count our attempts, and if we've
        # surpassed the limit, we stop
        self._connection_attempts += 1
        if (
            self._connection_attempts 
            >= self._connection_attempt_limit
        ):
            self.die()
            return
        self._state = 'waiting_till_connect'
        ba.apptimer(4, self._check_for_connection)
        self._connecting = False
        self._update_our_actor()