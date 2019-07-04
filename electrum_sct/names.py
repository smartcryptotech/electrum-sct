#!/usr/bin/env python
#
# Electrum-NYC - lightweight NewYorkCoin client
# Copyright (C) 2018 NewYorkCoin Developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

def split_name_script(decoded):
    # This case happens if a script was malformed and couldn't be decoded by
    # transaction.get_address_from_output_script.
    if decoded is None:
        return {"name_op": None, "address_scriptPubKey": decoded}

    # name_new TxOuts look like:
    # NAME_NEW (hash) 2DROP (Bitcoin TxOut)
    match = [ OP_NAME_NEW, OPPushDataGeneric, opcodes.OP_2DROP ]
    if match_decoded(decoded[:len(match)], match):
        return {"name_op": {"op": OP_NAME_NEW, "hash": decoded[1][1]}, "address_scriptPubKey": decoded[len(match):]}

    # name_firstupdate TxOuts look like:
    # NAME_FIRSTUPDATE (name) (rand) (value) 2DROP 2DROP (Bitcoin TxOut)
    match = [ OP_NAME_FIRSTUPDATE, OPPushDataGeneric, OPPushDataGeneric, OPPushDataGeneric, opcodes.OP_2DROP, opcodes.OP_2DROP ]
    if match_decoded(decoded[:len(match)], match):
        return {"name_op": {"op": OP_NAME_FIRSTUPDATE, "name": decoded[1][1], "rand": decoded[2][1], "value": decoded[3][1]}, "address_scriptPubKey": decoded[len(match):]}

    # name_update TxOuts look like:
    # NAME_UPDATE (name) (value) 2DROP DROP (Bitcoin TxOut)
    match = [ OP_NAME_UPDATE, OPPushDataGeneric, OPPushDataGeneric, opcodes.OP_2DROP, opcodes.OP_DROP ]
    if match_decoded(decoded[:len(match)], match):
        return {"name_op": {"op": OP_NAME_UPDATE, "name": decoded[1][1], "value": decoded[2][1]}, "address_scriptPubKey": decoded[len(match):]}

    return {"name_op": None, "address_scriptPubKey": decoded}

def get_name_op_from_output_script(_bytes):
    try:
        decoded = [x for x in script_GetOp(_bytes)]
    except MalformedBitcoinScript:
        decoded = None

    # Extract the name script if one is present.
    return split_name_script(decoded)["name_op"]

def name_op_to_script(name_op):
    if name_op is None:
        script = ''
    elif name_op["op"] == OP_NAME_NEW:
        validate_new_length(name_op)
        script = '51'                                 # OP_NAME_NEW
        script += push_script(bh2u(name_op["hash"]))
        script += '6d'                                # OP_2DROP
    elif name_op["op"] == OP_NAME_FIRSTUPDATE:
        validate_firstupdate_length(name_op)
        script = '52'                                 # OP_NAME_FIRSTUPDATE
        script += push_script(bh2u(name_op["name"]))
        script += push_script(bh2u(name_op["rand"]))
        script += push_script(bh2u(name_op["value"]))
        script += '6d'                                # OP_2DROP
        script += '6d'                                # OP_2DROP
    elif name_op["op"] == OP_NAME_UPDATE:
        validate_update_length(name_op)
        script = '53'                                 # OP_NAME_UPDATE
        script += push_script(bh2u(name_op["name"]))
        script += push_script(bh2u(name_op["value"]))
        script += '6d'                                # OP_2DROP
        script += '75'                                # OP_DROP
    else:
        raise BitcoinException('unknown name op: {}'.format(name_op))
    return script

def validate_new_length(name_op):
    validate_hash_length(name_op["hash"])

def validate_firstupdate_length(name_op):
    validate_rand_length(name_op["rand"])
    validate_anyupdate_length(name_op)

def validate_update_length(name_op):
    validate_anyupdate_length(name_op)

def validate_anyupdate_length(name_op):
    validate_identifier_length(name_op["name"])
    validate_value_length(name_op["value"])

def validate_hash_length(commitment):
    hash_length_requirement = 20

    hash_length = len(commitment)
    if hash_length != hash_length_requirement:
        raise BitcoinException('hash length {} is not equal to requirement of {}'.format(hash_length, hash_length_requirement))

def validate_rand_length(rand):
    rand_length_requirement = 20

    rand_length = len(rand)
    if rand_length != rand_length_requirement:
        raise BitcoinException('rand length {} is not equal to requirement of {}'.format(rand_length, rand_length_requirement))

def validate_identifier_length(identifier):
    identifier_length_limit = 255

    identifier_length = len(identifier)
    if identifier_length > identifier_length_limit:
        raise BitcoinException('identifier length {} exceeds limit of {}'.format(identifier_length, identifier_length_limit))

def validate_value_length(value):
    value_length_limit = 520

    value_length = len(value)
    if value_length > value_length_limit:
        raise BitcoinException('value length {} exceeds limit of {}'.format(value_length, value_length_limit))

def build_name_new(identifier, rand = None):
    validate_identifier_length(identifier)

    if rand is None:
        rand = os.urandom(20)

    to_hash = rand + identifier
    commitment = hash_160(to_hash)

    return {"op": OP_NAME_NEW, "hash": commitment}, rand

def name_identifier_to_scripthash(identifier_bytes):
    name_op = {"op": OP_NAME_UPDATE, "name": identifier_bytes, "value": bytes([])}
    script = name_op_to_script(name_op)
    script += '6a' # OP_RETURN

    return script_to_scripthash(script)


def format_name_identifier(identifier_bytes):
    try:
        identifier = identifier_bytes.decode("ascii")
    except UnicodeDecodeError:
        return format_name_identifier_unknown_hex(identifier_bytes)

    is_domain_namespace = identifier.startswith("d/")
    if is_domain_namespace:
        return format_name_identifier_domain(identifier)

    is_identity_namespace = identifier.startswith("id/")
    if is_identity_namespace:
        return format_name_identifier_identity(identifier)

    return format_name_identifier_unknown(identifier)


def format_name_identifier_domain(identifier):
    label = identifier[len("d/"):]

    if len(label) < 1:
        return format_name_identifier_unknown(identifier)

    # Source: https://github.com/newyorkcoin/proposals/blob/master/ifa-0001.md#keys
    if len(label) > 63:
        return format_name_identifier_unknown(identifier)

    # Source: https://github.com/newyorkcoin/proposals/blob/master/ifa-0001.md#keys
    label_regex = r"^(xn--)?[a-z0-9]+(-[a-z0-9]+)*$"
    label_match = re.match(label_regex, label)
    if label_match is None:
        return format_name_identifier_unknown(identifier)

    # Reject digits-only labels
    number_regex = r"^[0-9]+$"
    number_match = re.match(number_regex, label)
    if number_match is not None:
        return format_name_identifier_unknown(identifier)

    return "Domain " + label + ".bit"


def format_name_identifier_identity(identifier):
    label = identifier[len("id/"):]

    if len(label) < 1:
        return format_name_identifier_unknown(identifier)

    # Max id/ identifier length is 255 chars according to wiki spec.  But we
    # don't need to check for this, because that's also the max length of an
    # identifier under the NewYorkCoin consensus rules.

    # Same as d/ regex but without IDN prefix.
    # TODO: this doesn't exactly match the https://wiki.newyorkcoin.org spec.
    label_regex = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    label_match = re.match(label_regex, label)
    if label_match is None:
        return format_name_identifier_unknown(identifier)

    return "Identity " + label

def format_name_identifier_unknown(identifier):
    # Check for non-printable characters, and print ASCII if none are found.
    if identifier.isprintable():
        return 'Non-standard name "' + identifier + '"'

    return format_name_identifier_unknown_hex(identifier.encode("ascii"))


def format_name_identifier_unknown_hex(identifier_bytes):
    return "Non-standard hex name " + bh2u(identifier_bytes)


def format_name_value(identifier_bytes):
    try:
        identifier = identifier_bytes.decode("ascii")
    except UnicodeDecodeError:
        return format_name_value_hex(identifier_bytes)

    if not identifier.isprintable():
        return format_name_value_hex(identifier_bytes)

    return "ASCII " + identifier


def format_name_value_hex(identifier_bytes):
    return "Hex " + bh2u(identifier_bytes)


def format_name_op(name_op):
    if name_op is None:
        return ''
    if "hash" in name_op:
        formatted_hash = "Commitment = " + bh2u(name_op["hash"])
    if "rand" in name_op:
        formatted_rand = "Salt = " + bh2u(name_op["rand"])
    if "name" in name_op:
        formatted_name = "Name = " + format_name_identifier(name_op["name"])
    if "value" in name_op:
        formatted_value = "Data = " + format_name_value(name_op["value"])

    if name_op["op"] == OP_NAME_NEW:
        return "\tPre-Registration\n\t\t" + formatted_hash
    if name_op["op"] == OP_NAME_FIRSTUPDATE:
        return "\tRegistration\n\t\t" + formatted_name + "\n\t\t" + formatted_rand + "\n\t\t" + formatted_value
    if name_op["op"] == OP_NAME_UPDATE:
        return "\tUpdate\n\t\t" + formatted_name + "\n\t\t" + formatted_value


def get_default_name_tx_label(wallet, tx):
    for idx, o in enumerate(tx.outputs()):
        name_op = o.name_op
        if name_op is not None:
            # TODO: Handle multiple atomic name ops.
            name_input_is_mine, name_output_is_mine, name_value_is_unchanged = get_wallet_name_delta(wallet, tx)
            if not name_input_is_mine and not name_output_is_mine:
                return None
            if name_input_is_mine and not name_output_is_mine:
                return "Transfer (Outgoing): " + format_name_identifier(name_op["name"])
            if not name_input_is_mine and name_output_is_mine:
                # A name_new transaction isn't expected to have a name input,
                # so we don't consider it a transfer.
                if name_op["op"] != OP_NAME_NEW:
                    return "Transfer (Incoming): " + format_name_identifier(name_op["name"])
            if name_op["op"] == OP_NAME_NEW:
                # Get the address where the NAME_NEW was sent to
                addr = o.address
                # Look for other transactions for this address, which might
                # include the NAME_FIRSTUPDATE
                addr_history = wallet.get_address_history(addr)
                for addr_txid, addr_height in addr_history:
                    # Examine a candidate tx that might be the NAME_FIRSTUPDATE
                    addr_tx = wallet.db.transactions.get(addr_txid)
                    # Look at all the candidate's inputs to make sure it's
                    # actually spending the NAME_NEW
                    for addr_tx_input in addr_tx.inputs():
                        if addr_tx_input['prevout_hash'] == tx.txid():
                            if addr_tx_input['prevout_n'] == idx:
                                # We've confirmed that it spends the NAME_NEW.
                                # Look at the outputs to find the
                                # NAME_FIRSTUPDATE.
                                for addr_tx_output in addr_tx.outputs():
                                    if addr_tx_output.name_op is not None:
                                        # We've found a name output; now we
                                        # check for an identifier.
                                        if 'name' in addr_tx_output.name_op:
                                            return "Pre-Registration: " + format_name_identifier(addr_tx_output.name_op['name'])

                # Look for queued transactions that spend the NAME_NEW
                for addr_txid in wallet.db.queued_transactions:
                    addr_tx_queue_item = wallet.db.queued_transactions[addr_txid]
                    # Check whether the queued transaction is contingent on the NAME_NEW transaction
                    if addr_tx_queue_item['sendWhen']['txid'] == tx.txid():
                        addr_tx = Transaction(addr_tx_queue_item['tx'])
                        # Look at all the candidate's inputs to make sure it's
                        # actually spending the NAME_NEW
                        for addr_tx_input in addr_tx.inputs():
                            if addr_tx_input['prevout_hash'] == tx.txid():
                                if addr_tx_input['prevout_n'] == idx:
                                    # We've confirmed that it spends the NAME_NEW.
                                    # Look at the outputs to find the
                                    # NAME_FIRSTUPDATE.
                                    for addr_tx_output in addr_tx.outputs():
                                        if addr_tx_output.name_op is not None:
                                            # We've found a name output; now we
                                            # check for an identifier.
                                            if 'name' in addr_tx_output.name_op:
                                                return "Pre-Registration: " + format_name_identifier(addr_tx_output.name_op['name'])

                # A name_new transaction doesn't have a visible 'name' field,
                # so there's nothing to format if we can't find the name
                # elsewhere in the wallet.
                return "Pre-Registration"
            if name_op["op"] == OP_NAME_FIRSTUPDATE:
                return "Registration: " + format_name_identifier(name_op["name"])
            if name_op["op"] == OP_NAME_UPDATE:
                if name_value_is_unchanged:
                    return "Renew: " + format_name_identifier(name_op["name"])
                else:
                    return "Update: " + format_name_identifier(name_op["name"])
    return None


def get_wallet_name_delta(wallet, tx):
    name_input_is_mine = False
    name_output_is_mine = False

    name_input_value = None
    name_output_value = None

    for txin in tx.inputs():
        addr = wallet.get_txin_address(txin)
        if wallet.is_mine(addr):
            prev_tx = wallet.db.transactions.get(txin['prevout_hash'])
            if prev_tx.outputs()[txin['prevout_n']].name_op is not None:
                name_input_is_mine = True
                if 'value' in prev_tx.outputs()[txin['prevout_n']].name_op:
                    name_input_value = prev_tx.outputs()[txin['prevout_n']].name_op['value']
    for o in tx.outputs():
        if o.name_op is not None and wallet.is_mine(o.address):
            name_output_is_mine = True
            if 'value' in o.name_op:
                name_output_value = o.name_op['value']

    name_value_is_unchanged = name_input_value == name_output_value

    return name_input_is_mine, name_output_is_mine, name_value_is_unchanged


def name_expires_in(name_height, chain_height):
    if name_height <= 0:
        return None

    return name_height - chain_height + 36000


import binascii
import os
import re

from .bitcoin import push_script, script_to_scripthash
from .crypto import hash_160
from .transaction import MalformedBitcoinScript, match_decoded, opcodes, OPPushDataGeneric, script_GetOp, Transaction
from .util import bh2u, BitcoinException

OP_NAME_NEW = opcodes.OP_1
OP_NAME_FIRSTUPDATE = opcodes.OP_2
OP_NAME_UPDATE = opcodes.OP_3

