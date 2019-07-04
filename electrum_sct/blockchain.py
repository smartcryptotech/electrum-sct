# Electrum - lightweight Bitcoin client Copyright (C) 2012 thomasv@ecdsa.org
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
import os
import threading
from typing import Optional, Dict

from . import util
from .bitcoin import hash_encode, int_to_hex, rev_hex
from .crypto import sha256d
from . import constants
from .util import bfh, bh2u
from .simple_config import SimpleConfig
from decimal import Decimal
from decimal import getcontext
from . import auxpow

HEADER_SIZE = 80  # bytes

try:
    import scrypt
    getPoWHash = lambda x: scrypt.hash(x, x, N=1024, r=1, p=1, buflen=32)
except ImportError:
    util.print_msg("Warning: package scrypt not available; synchronization could be very slow")
    from .scrypt import scrypt_1024_1_1_80 as getPoWHash

MAX_TARGET = 0x00000FFFFF000000000000000000000000000000000000000000000000000000


class MissingHeader(Exception):
    pass

class InvalidHeader(Exception):
    pass

def serialize_header(header_dict: dict) -> str:
    s = int_to_hex(header_dict['version'], 4) \
        + rev_hex(header_dict['prev_block_hash']) \
        + rev_hex(header_dict['merkle_root']) \
        + int_to_hex(int(header_dict['timestamp']), 4) \
        + int_to_hex(int(header_dict['bits']), 4) \
        + int_to_hex(int(header_dict['nonce']), 4)
    return s

# If expect_trailing_data, returns start position of trailing data
def deserialize_header(s: bytes, height: int, expect_trailing_data=False, start_position=0):
    if not s:
        raise InvalidHeader('Invalid header: {}'.format(s))
    if len(s) - start_position < HEADER_SIZE:
        raise InvalidHeader('Invalid header length: {}'.format(len(s) - start_position))
    hex_to_int = lambda s: int.from_bytes(s, byteorder='little')
    h = {}
    h['version'] = hex_to_int(s[start_position+0:start_position+4])
    h['prev_block_hash'] = hash_encode(s[start_position+4:start_position+36])
    h['merkle_root'] = hash_encode(s[start_position+36:start_position+68])
    h['timestamp'] = hex_to_int(s[start_position+68:start_position+72])
    h['bits'] = hex_to_int(s[start_position+72:start_position+76])
    h['nonce'] = hex_to_int(s[start_position+76:start_position+80])
    h['block_height'] = height

    if auxpow.auxpow_active(h) and height > constants.net.max_checkpoint():
        if expect_trailing_data:
            h['auxpow'], start_position = auxpow.deserialize_auxpow_header(h, s, expect_trailing_data=True, start_position=start_position+HEADER_SIZE)
        else:
            h['auxpow'] = auxpow.deserialize_auxpow_header(h, s, start_position=start_position+HEADER_SIZE)
    else:
        if expect_trailing_data:
            start_position = start_position+HEADER_SIZE
        elif len(s) - start_position != HEADER_SIZE:
            raise Exception('Invalid header length: {}'.format(len(s) - start_position))

    if expect_trailing_data:
        return h, start_position

    return h

def hash_header(header: dict) -> str:
    if header is None:
        return '0' * 64
    if header.get('prev_block_hash') is None:
        header['prev_block_hash'] = '00'*32
    return hash_raw_header(serialize_header(header))


def hash_raw_header(header: str) -> str:
    return hash_encode(sha256d(bfh(header)))

def pow_hash_header(header):
    return hash_encode(getPoWHash(bfh(serialize_header(header))))

# key: blockhash hex at forkpoint
# the chain at some key is the best chain that includes the given hash
blockchains = {}  # type: Dict[str, Blockchain]
blockchains_lock = threading.RLock()


def read_blockchains(config: 'SimpleConfig'):
    best_chain = Blockchain(config=config,
                            forkpoint=0,
                            parent=None,
                            forkpoint_hash=constants.net.GENESIS,
                            prev_hash=None)
    blockchains[constants.net.GENESIS] = best_chain
    # consistency checks
    if best_chain.height() > constants.net.max_checkpoint():
        header_after_cp = best_chain.read_header(constants.net.max_checkpoint()+1)
        if not header_after_cp or not best_chain.can_connect(header_after_cp, check_height=False):
            util.print_error("[blockchain] deleting best chain. cannot connect header after last cp to last cp.")
            os.unlink(best_chain.path())
            best_chain.update_size()
    # forks
    fdir = os.path.join(util.get_headers_dir(config), 'forks')
    util.make_dir(fdir)
    # files are named as: fork2_{forkpoint}_{prev_hash}_{first_hash}
    l = filter(lambda x: x.startswith('fork2_') and '.' not in x, os.listdir(fdir))
    l = sorted(l, key=lambda x: int(x.split('_')[1]))  # sort by forkpoint

    def delete_chain(filename, reason):
        util.print_error(f"[blockchain] deleting chain {filename}: {reason}")
        os.unlink(os.path.join(fdir, filename))

    def instantiate_chain(filename):
        __, forkpoint, prev_hash, first_hash = filename.split('_')
        forkpoint = int(forkpoint)
        prev_hash = (64-len(prev_hash)) * "0" + prev_hash  # left-pad with zeroes
        first_hash = (64-len(first_hash)) * "0" + first_hash
        # forks below the max checkpoint are not allowed
        if forkpoint <= constants.net.max_checkpoint():
            delete_chain(filename, "deleting fork below max checkpoint")
            return
        # find parent (sorting by forkpoint guarantees it's already instantiated)
        for parent in blockchains.values():
            if parent.check_hash(forkpoint - 1, prev_hash):
                break
        else:
            delete_chain(filename, "cannot find parent for chain")
            return
        b = Blockchain(config=config,
                       forkpoint=forkpoint,
                       parent=parent,
                       forkpoint_hash=first_hash,
                       prev_hash=prev_hash)
        # consistency checks
        h = b.read_header(b.forkpoint)
        if first_hash != hash_header(h):
            delete_chain(filename, "incorrect first hash for chain")
            return
        if not b.parent.can_connect(h, check_height=False):
            delete_chain(filename, "cannot connect chain to parent")
            return
        chain_id = b.get_id()
        assert first_hash == chain_id, (first_hash, chain_id)
        blockchains[chain_id] = b

    for filename in l:
        instantiate_chain(filename)


def get_best_chain() -> 'Blockchain':
    return blockchains[constants.net.GENESIS]

# block hash -> chain work; up to and including that block
_CHAINWORK_CACHE = {
    "0000000000000000000000000000000000000000000000000000000000000000": 0,  # virtual block at height -1
}  # type: Dict[str, int]


class Blockchain(util.PrintError):
    """
    Manages blockchain headers and their verification
    """

    def __init__(self, config: SimpleConfig, forkpoint: int, parent: Optional['Blockchain'],
                 forkpoint_hash: str, prev_hash: Optional[str]):
        assert isinstance(forkpoint_hash, str) and len(forkpoint_hash) == 64, forkpoint_hash
        assert (prev_hash is None) or (isinstance(prev_hash, str) and len(prev_hash) == 64), prev_hash
        # assert (parent is None) == (forkpoint == 0)
        if 0 < forkpoint <= constants.net.max_checkpoint():
            raise Exception(f"cannot fork below max checkpoint. forkpoint: {forkpoint}")
        self.config = config
        self.forkpoint = forkpoint  # height of first header
        self.parent = parent
        self._forkpoint_hash = forkpoint_hash  # blockhash at forkpoint. "first hash"
        self._prev_hash = prev_hash  # blockhash immediately before forkpoint
        self.lock = threading.RLock()
        self.update_size()

    def with_lock(func):
        def func_wrapper(self, *args, **kwargs):
            with self.lock:
                return func(self, *args, **kwargs)
        return func_wrapper

    @property
    def checkpoints(self):
        return constants.net.CHECKPOINTS

    def get_max_child(self) -> Optional[int]:
        with blockchains_lock: chains = list(blockchains.values())
        children = list(filter(lambda y: y.parent==self, chains))
        return max([x.forkpoint for x in children]) if children else None

    def get_max_forkpoint(self) -> int:
        """Returns the max height where there is a fork
        related to this chain.
        """
        mc = self.get_max_child()
        return mc if mc is not None else self.forkpoint

    @with_lock
    def get_branch_size(self) -> int:
        return self.height() - self.get_max_forkpoint() + 1

    def get_name(self) -> str:
        return self.get_hash(self.get_max_forkpoint()).lstrip('0')[0:10]

    def check_header(self, header: dict) -> bool:
        header_hash = hash_header(header)
        height = header.get('block_height')
        return self.check_hash(height, header_hash)

    def check_hash(self, height: int, header_hash: str) -> bool:
        """Returns whether the hash of the block at given height
        is the given hash.
        """
        assert isinstance(header_hash, str) and len(header_hash) == 64, header_hash  # hex
        try:
            return header_hash == self.get_hash(height)
        except Exception:
            return False

    def fork(parent, header: dict) -> 'Blockchain':
        if not parent.can_connect(header, check_height=False):
            raise Exception("forking header does not connect to parent chain")
        forkpoint = header.get('block_height')
        self = Blockchain(config=parent.config,
                          forkpoint=forkpoint,
                          parent=parent,
                          forkpoint_hash=hash_header(header),
                          prev_hash=parent.get_hash(forkpoint-1))
        open(self.path(), 'w+').close()
        self.save_header(header)
        # put into global dict. note that in some cases
        # save_header might have already put it there but that's OK
        chain_id = self.get_id()
        with blockchains_lock:
            blockchains[chain_id] = self
        return self

    @with_lock
    def height(self) -> int:
        return self.forkpoint + self.size() - 1

    @with_lock
    def size(self) -> int:
        return self._size

    @with_lock
    def update_size(self) -> None:
        p = self.path()
        self._size = os.path.getsize(p)//HEADER_SIZE if os.path.exists(p) else 0

    @classmethod
    def verify_header(cls, header: dict, prev_hash: str, target: int, expected_header_hash: str=None) -> None:
        _hash = hash_header(header)
        _powhash = pow_hash_header(header)
        # Don't verify AuxPoW when covered by a checkpoint
#       if header.get('block_height') > constants.net.max_checkpoint():
#            _pow_hash = auxpow.hash_parent_header(header)
        if expected_header_hash and expected_header_hash != _hash:
            print("Hash Mismatches with expected: {} vs {}".format(expected_header_hash, _hash))
            raise Exception("hash mismatches with expected: {} vs {}".format(expected_header_hash, _hash))
        if prev_hash != header.get('prev_block_hash'):
            print("prev hash mismatch: {} vs {}".format(prev_hash, header.get('prev_block_hash')))
            raise Exception("prev hash mismatch: %s vs %s" % (prev_hash, header.get('prev_block_hash')))
        if constants.net.TESTNET:
            return
        #bits = cls.target_to_bits(target)
        #if bits != header.get('bits'):
        #    print("Bits Mismatch {} vs {}".format(bits, header.get('bits')))
        #    raise Exception("bits mismatch: %s vs %s" % (bits, header.get('bits')))
        # Don't verify AuxPoW when covered by a checkpoint
#       if header.get('block_height') > constants.net.max_checkpoint():
        block_hash_as_num = int.from_bytes(bfh(_powhash), byteorder='big')
        #if block_hash_as_num > target:
        #   print(f"insufficient proof of work: {block_hash_as_num} vs target {target}")
        #   raise Exception(f"insufficient proof of work: {block_hash_as_num} vs target {target}")

    def verify_chunk(self, index: int, data: bytes) -> bytes:
        stripped = bytearray()
        start_position = 0
        start_height = index * 2016
        prev_hash = self.get_hash(start_height - 1)
        target = self.get_target(index-1)
        i = 0
        while start_position < len(data):
            height = start_height + i
            try:
                expected_header_hash = self.get_hash(height)
            except MissingHeader:
                expected_header_hash = None

            # Strip auxpow header for disk
            stripped.extend(data[start_position:start_position+HEADER_SIZE])

            header, start_position = deserialize_header(data, index*2016 + i, expect_trailing_data=True, start_position=start_position)
            self.verify_header(header, prev_hash, target, expected_header_hash)
            prev_hash = hash_header(header)

            i = i + 1

        return bytes(stripped)

    @with_lock
    def path(self):
        d = util.get_headers_dir(self.config)
        if self.parent is None:
            filename = 'blockchain_headers'
        else:
            assert self.forkpoint > 0, self.forkpoint
            prev_hash = self._prev_hash.lstrip('0')
            first_hash = self._forkpoint_hash.lstrip('0')
            basename = f'fork2_{self.forkpoint}_{prev_hash}_{first_hash}'
            filename = os.path.join('forks', basename)
        return os.path.join(d, filename)

    @with_lock
    def save_chunk(self, index: int, chunk: bytes):
        assert index >= 0, index
        chunk_within_checkpoint_region = index < len(self.checkpoints)
        # chunks in checkpoint region are the responsibility of the 'main chain'
        if chunk_within_checkpoint_region and self.parent is not None:
            main_chain = get_best_chain()
            main_chain.save_chunk(index, chunk)
            return

        delta_height = (index * 2016 - self.forkpoint)
        delta_bytes = delta_height * HEADER_SIZE
        # if this chunk contains our forkpoint, only save the part after forkpoint
        # (the part before is the responsibility of the parent)
        if delta_bytes < 0:
            chunk = chunk[-delta_bytes:]
            delta_bytes = 0
        truncate = not chunk_within_checkpoint_region
        self.write(chunk, delta_bytes, truncate)
        self.swap_with_parent()

    def swap_with_parent(self) -> None:
        parent_lock = self.parent.lock if self.parent is not None else threading.Lock()
        with parent_lock, self.lock, blockchains_lock:  # this order should not deadlock
            # do the swap; possibly multiple ones
            cnt = 0
            while self._swap_with_parent():
                cnt += 1
                if cnt > len(blockchains):  # make sure we are making progress
                    raise Exception(f'swapping fork with parent too many times: {cnt}')

    def _swap_with_parent(self) -> bool:
        """Check if this chain became stronger than its parent, and swap
        the underlying files if so. The Blockchain instances will keep
        'containing' the same headers, but their ids change and so
        they will be stored in different files."""
        if self.parent is None:
            return False
        if self.parent.get_chainwork() >= self.get_chainwork():
            return False
        self.print_error("swap", self.forkpoint, self.parent.forkpoint)
        parent_branch_size = self.parent.height() - self.forkpoint + 1
        forkpoint = self.forkpoint  # type: Optional[int]
        parent = self.parent  # type: Optional[Blockchain]
        child_old_id = self.get_id()
        parent_old_id = parent.get_id()
        # swap files
        # child takes parent's name
        # parent's new name will be something new (not child's old name)
        self.assert_headers_file_available(self.path())
        child_old_name = self.path()
        with open(self.path(), 'rb') as f:
            my_data = f.read()
        self.assert_headers_file_available(parent.path())
        with open(parent.path(), 'rb') as f:
            f.seek((forkpoint - parent.forkpoint)*HEADER_SIZE)
            parent_data = f.read(parent_branch_size*HEADER_SIZE)
        self.write(parent_data, 0)
        parent.write(my_data, (forkpoint - parent.forkpoint)*HEADER_SIZE)
        # swap parameters
        self.parent, parent.parent = parent.parent, self  # type: Optional[Blockchain], Optional[Blockchain]
        self.forkpoint, parent.forkpoint = parent.forkpoint, self.forkpoint
        self._forkpoint_hash, parent._forkpoint_hash = parent._forkpoint_hash, hash_raw_header(bh2u(parent_data[:HEADER_SIZE]))
        self._prev_hash, parent._prev_hash = parent._prev_hash, self._prev_hash
        # parent's new name
        os.replace(child_old_name, parent.path())
        self.update_size()
        parent.update_size()
        # update pointers
        blockchains.pop(child_old_id, None)
        blockchains.pop(parent_old_id, None)
        blockchains[self.get_id()] = self
        blockchains[parent.get_id()] = parent
        return True

    def get_id(self) -> str:
        return self._forkpoint_hash

    def assert_headers_file_available(self, path):
        if os.path.exists(path):
            return
        elif not os.path.exists(util.get_headers_dir(self.config)):
            raise FileNotFoundError('Electrum-NYC headers_dir does not exist. Was it deleted while running?')
        else:
            raise FileNotFoundError('Cannot find headers file but headers_dir is there. Should be at {}'.format(path))

    @with_lock
    def write(self, data: bytes, offset: int, truncate: bool=True) -> None:
        filename = self.path()
        self.assert_headers_file_available(filename)
        with open(filename, 'rb+') as f:
            if truncate and offset != self._size * HEADER_SIZE:
                f.seek(offset)
                f.truncate()
            f.seek(offset)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        self.update_size()

    @with_lock
    def save_header(self, header: dict) -> None:
        delta = header.get('block_height') - self.forkpoint
        data = bfh(serialize_header(header))
        # headers are only _appended_ to the end:
        assert delta == self.size(), (delta, self.size())
        assert len(data) == HEADER_SIZE
        self.write(data, delta*HEADER_SIZE)
        self.swap_with_parent()

    @with_lock
    def read_header(self, height: int) -> Optional[dict]:
        if height < 0:
            return
        if height < self.forkpoint:
            return self.parent.read_header(height)
        if height > self.height():
            return
        delta = height - self.forkpoint
        name = self.path()
        self.assert_headers_file_available(name)
        with open(name, 'rb') as f:
            f.seek(delta * HEADER_SIZE)
            h = f.read(HEADER_SIZE)
            if len(h) < HEADER_SIZE:
                raise Exception('Expected to read a full header. This was only {} bytes'.format(len(h)))
        if h == bytes([0])*HEADER_SIZE:
            return None
        return deserialize_header(h, height)

    def header_at_tip(self) -> Optional[dict]:
        """Return latest header."""
        height = self.height()
        return self.read_header(height)

    def get_hash(self, height: int) -> str:
        def is_height_checkpoint():
            within_cp_range = height <= constants.net.max_checkpoint()
            at_chunk_boundary = (height+1) % 2016 == 0
            return within_cp_range and at_chunk_boundary

        if height == -1:
            return '0000000000000000000000000000000000000000000000000000000000000000'
        elif height == 0:
            return constants.net.GENESIS
        elif is_height_checkpoint():
            index = height // 2016
            h, t = self.checkpoints[index]
            return h
        else:
            header = self.read_header(height)
            if header is None:
                raise MissingHeader(height)
            return hash_header(header)

    def get_timestamp(self, height):
        if height < len(self.checkpoints) * 2016 and (height+1) % 2016 == 0:
            index = height // 2016
            _, _, ts = self.checkpoints[index]
            return ts
        return self.read_header(height).get('timestamp')

    def get_target(self, height, chain={}):
        if constants.net.TESTNET:
            return 0, 0
        if height <= 28:
            return 0x1e0ffff0, 0x00000FFFF0000000000000000000000000000000000000000000000000000000
        index = height // 2016
        print("index %d" % index + " height %d" % height)
        if index < len(self.checkpoints) and (height % 2016 == 0):
            print("Bailing early index < len(self.checkpoints)")
            _, t, b, _ = self.checkpoints[index]
            return b, t
        if height < 4800000:
            print("returning kgw")
            return self.KimotoGravityWell(height, chain)
        else:
            print("returning digishield")
            return self.get_digishield_target(height, chain)

    def convbits(self, new_target):
        c = ("%064x" % int(new_target))[2:]
        while c[:2] == '00' and len(c) > 6:
            c = c[2:]
        bitsN, bitsBase = len(c) // 2, int('0x' + c[:6], 16)
        if bitsBase >= 0x800000:
            bitsN += 1
            bitsBase >>= 8
        new_bits = bitsN << 24 | bitsBase
        return new_bits

    def convlegacybits(self, new_target):
        c = ("%064x" % int(new_target))[2:]
        while c[:2] == '00' and len(c) > 6:
            c = c[2:]
        bitsN, bitsBase = len(c) // 2, int('0x' + c[:6], 16)
        newbase = 0
        if bitsN <= 3:
            newbase = bitsBase << (8 * (3-bitsN))
        else:
            newbase = bitsBase >> (8 * (bitsN - 3))
        if (newbase * 0x00800000) == 1:
            bitsN += 1
            newbase >>= 8
        new_bits = bitsN << 24 | newbase
        final_bits = new_bits
        if (newbase * 0x00800000) == 1:

            final_bits = new_bits | 0x00800000
        else:
            final_bits = new_bits | 0
        return final_bits

    def convbignum(self, bits):
        bitsN = (bits >> 24) & 0xff
        if not (bitsN >= 0x03 and bitsN <= 0x1e):
            raise BaseException("First part of bits should be in [0x03, 0x1e]")
        bitsBase = bits & 0xffffff
        if not (bitsBase >= 0x8000 and bitsBase <= 0x7fffff):
            raise BaseException("Second part of bits should be in [0x8000, 0x7fffff]")
        if bitsN <= 0x03:
            target = bitsBase >> (8 * (0x03 - bitsN))
        else:
            target = bitsBase << (8 * (bitsN - 0x03))
        return target

    def convlegacybignum(self,bits):
        bitsN = (bits >> 24)
        fNegative = False
        if (bits & 0x00800000) != 0:

            fNegative = True
        if not (bitsN >= 0x03 and bitsN <= 0x1e):
            raise BaseException("First part of bits should be in [0x03, 0x1e]")
        bitsBase = bits & 0x007ffffff
        if not (bitsBase >= 0x8000 and bitsBase <= 0x7fffff):
            raise BaseException("Second part of bits should be in [0x8000, 0x7fffff]")
        if bitsN <= 3:
            target = bitsBase >> (8 * (3 - bitsN))
        else:
            target = bitsBase << (8 * (bitsN - 3))
        if fNegative == True:
            target = -target
        return target

    @classmethod
    def bits_to_target(cls, bits: int) -> int:
        bitsN = (bits >> 24) & 0xff
        if not (0x03 <= bitsN <= 0x1d):
            raise Exception("First part of bits should be in [0x03, 0x1d]")
        bitsBase = bits & 0xffffff
        if not (0x8000 <= bitsBase <= 0x7fffff):
            raise Exception("Second part of bits should be in [0x8000, 0x7fffff]")
        return bitsBase << (8 * (bitsN-3))

    @classmethod
    def target_to_bits(cls, target: int) -> int:
        c = ("%064x" % target)[2:]
        while c[:2] == '00' and len(c) > 6:
            c = c[2:]
        bitsN, bitsBase = len(c) // 2, int.from_bytes(bfh(c[:6]), byteorder='big')
        if bitsBase >= 0x800000:
            bitsN += 1
            bitsBase >>= 8
        return bitsN << 24 | bitsBase

    def chainwork_of_header_at_height(self, height: int) -> int:
        """work done by single header at given height"""
        chunk_idx = height // 2016 - 1
        target = self.get_target(chunk_idx)
        work = ((2 ** 256 - target - 1) // (target + 1)) + 1
        return work

    @with_lock
    def get_chainwork(self, height=None) -> int:
        if height is None:
            height = max(0, self.height())
        if constants.net.TESTNET:
            # On testnet/regtest, difficulty works somewhat different.
            # It's out of scope to properly implement that.
            return height
        last_retarget = height // 2016 * 2016 - 1
        cached_height = last_retarget
        while _CHAINWORK_CACHE.get(self.get_hash(cached_height)) is None:
            if cached_height <= -1:
                break
            cached_height -= 2016
        assert cached_height >= -1, cached_height
        running_total = _CHAINWORK_CACHE[self.get_hash(cached_height)]
        while cached_height < last_retarget:
            cached_height += 2016
            work_in_single_header = self.chainwork_of_header_at_height(cached_height)
            work_in_chunk = 2016 * work_in_single_header
            running_total += work_in_chunk
            _CHAINWORK_CACHE[self.get_hash(cached_height)] = running_total
        cached_height += 2016
        work_in_single_header = self.chainwork_of_header_at_height(cached_height)
        work_in_last_partial_chunk = (height % 2016 + 1) * work_in_single_header
        return running_total + work_in_last_partial_chunk

    def can_connect(self, header: dict, check_height: bool=True) -> bool:
        if header is None:
            return False
        height = header['block_height']
        if check_height and self.height() != height - 1:
            self.print_error("cannot connect at height", height)
            return False
        if height == 0:
            return hash_header(header) == constants.net.GENESIS
        try:
            prev_hash = self.get_hash(height - 1)
        except:
            print("Couldnt Find Previous Hash For Block at {0}".format(height - 1))
            return False

        if prev_hash != header.get('prev_block_hash'):
            print("Invalid PrevHash")
            return False
        try:
            bits, target = self.get_target(height)
        except MissingHeader:
            return False
        try:
            self.verify_header(header, prev_hash, target)
        except BaseException as e:
            print("Failed to Verify Header: {0}".format(e))
            return False
        return True

    def connect_chunk(self, idx: int, hexdata: str) -> bool:
        assert idx >= 0, idx
        try:
            data = bfh(hexdata)
            # verify_chunk also strips the AuxPoW headers
            data = self.verify_chunk(idx, data)
            #self.print_error("validated chunk %d" % idx)
            self.save_chunk(idx, data)
            return True
        except BaseException as e:
            self.print_error(f'verify_chunk idx {idx} failed: {repr(e)}')
            return False

    def get_checkpoints(self):
        # for each chunk, store the hash of the last block and the target after the chunk
        cp = []

        # NewYorkCoin: don't generate checkpoints for unexpired names, because
        # otherwise we'll need to fetch chunks on demand during name lookups,
        # which will add some latency.  TODO: Allow user-configurable pre-
        # fetching of checkpointed unexpired chunks.
        #n = self.height() // 2016
        n = (self.height() - 36000) // 2016

        for index in range(n):
            h = self.get_hash((index+1) * 2016 -1)
            target = self.get_target(index)
            cp.append((h, target))
        return cp

    def get_digishield_target(self, height, chain={}):
        if chain is None:
            chain = {}

        nPowTargetTimespan = 60 #1 minute

        nPowTargetSpacing = 30 # .5 minute
        nPowTargetSpacingDigisheld = 30 #.5 minute

        DifficultyAdjustmentIntervalDigisheld = nPowTargetSpacingDigisheld // nPowTargetSpacing #1

        AdjustmentInterval = DifficultyAdjustmentIntervalDigisheld

        blockstogoback = AdjustmentInterval - 1
        if (height != AdjustmentInterval):
            blockstogoback = AdjustmentInterval

        last_height = height - 1
        first_height = last_height - blockstogoback

        TargetTimespan = nPowTargetTimespan

        first = chain.get(first_height)
        if first is None:
            first = self.read_header(first_height)
        last = chain.get(last_height)
        if last is None:
            last = self.read_header(last_height)

        nActualTimespan = last.get('timestamp') - first.get('timestamp')

        nActualTimespan = TargetTimespan + int(float(nActualTimespan - TargetTimespan) / float(8))
        nActualTimespan = max(nActualTimespan, TargetTimespan - int(float(TargetTimespan) / float(4)))
        nActualTimespan = min(nActualTimespan, TargetTimespan + int(float(TargetTimespan) / float(2)))

        bits = last.get('bits')
        bnNew = self.convbignum(bits)
        if height % AdjustmentInterval != 0:
            return bits, bnNew

        # retarget
        bnNew *= nActualTimespan
        bnNew //= TargetTimespan
        bnNew = min(bnNew, MAX_TARGET)

        new_bits = self.convbits(bnNew)
        return new_bits, bnNew

    def KimotoGravityWell(self, height, chain={}):
        BlocksTargetSpacing = 0.5 * 60  # 30 seconds
        TimeDaySeconds = 60 * 60 * 24
        PastSecondsMin = TimeDaySeconds * 0.01
        PastSecondsMax = TimeDaySeconds * 0.14
        PastBlocksMin = PastSecondsMin / BlocksTargetSpacing
        PastBlocksMax = PastSecondsMax / BlocksTargetSpacing
        PastBlocksMass = 0

        new_target = 0
        new_bits = 0
        BlockReadingIndex = height - 1
        BlockLastSolvedIndex = height - 1
        TargetBlocksSpacingSeconds = BlocksTargetSpacing
        PastRateAdjustmentRatio = float(1)
        bnProofOfWorkLimit = 0x00000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF



        if (BlockLastSolvedIndex <= 0 or BlockLastSolvedIndex < PastSecondsMin):
            print("maybe here")
            new_target = bnProofOfWorkLimit
            new_bits = self.convbits(new_target)
            return new_bits, new_target

        last = chain.get(BlockLastSolvedIndex)
        if last == None:
            last = self.read_header(BlockLastSolvedIndex)


        for i in range(1, int(PastBlocksMax)+1):
            if PastBlocksMax > 0 and i > PastBlocksMax:
                break;
            PastBlocksMass = i

            reading = chain.get(BlockReadingIndex)
            if reading == None:
                reading = self.read_header(BlockReadingIndex)
                chain[BlockReadingIndex] = reading

            if (reading == None or last == None):
                raise BaseException("Could not find previous blocks when calculating difficulty reading: " + str(BlockReadingIndex) + ", last: " + str(BlockLastSolvedIndex) + ", height: " + str(height))

            if (i == 1):
                PastDifficultyAverage = self.convbignum(reading.get('bits'))
            else:
                pastBits = reading.get('bits')
                PastDifficultyAverage = float(((self.convbignum(pastBits))- PastDifficultyAveragePrev) / float(i)) + PastDifficultyAveragePrev

            PastDifficultyAveragePrev = PastDifficultyAverage
            #print("Height %d" % reading.get('block_height') + " timestamp %d" % reading.get('timestamp'))
            PastRateActualSeconds = last.get('timestamp') - reading.get('timestamp')
            PastRateTargetSeconds = TargetBlocksSpacingSeconds * PastBlocksMass
            PastRateAdjustmentRatio = float(1.0)
            if (PastRateActualSeconds < 0):

                PastRateActualSeconds = 0.0

            if (PastRateActualSeconds != 0 and PastRateTargetSeconds != 0):
                PastRateAdjustmentRatio = float(PastRateTargetSeconds) / float(PastRateActualSeconds)
                #print("PastRateAactualseconds %d" % PastRateActualSeconds)

            EventHorizonDeviation = 1 + ((0.7084) * pow((float(PastBlocksMass)/float(144)), float(-1.228)))
            EventHorizonDeviationFast = EventHorizonDeviation
            EventHorizonDeviationSlow = float(1) / float(EventHorizonDeviation)

            if (PastBlocksMass >= PastBlocksMin):

                if ((PastRateAdjustmentRatio <= EventHorizonDeviationSlow) or (PastRateAdjustmentRatio >= EventHorizonDeviationFast)):
                    break
                if (BlockReadingIndex < 1):
                    break


            BlockReadingIndex = BlockReadingIndex - 1


        #print("PastDifficultyAverage %d" % PastDifficultyAverage)
        bnNew = PastDifficultyAverage
        if (PastRateActualSeconds != 0 and PastRateTargetSeconds != 0):
            bnNew *= float(PastRateActualSeconds)
            bnNew /= float(PastRateTargetSeconds)
        else:
            print("PastDifficultyAverage Unaltered")
        if (bnNew > bnProofOfWorkLimit):
            #print("bnNew greater than proof of work limit")
            bnNew = bnProofOfWorkLimit

        # new target
        new_target = bnNew

        new_bits = self.convbits(new_target)

        #print("bits %d" % new_bits , "(", hex(new_bits),")")
        #print("target %d" % new_target)
        #print("PastRateAdjustmentRatio=",PastRateAdjustmentRatio,"EventHorizonDeviationSlow",EventHorizonDeviationSlow,"PastSecondsMin=",PastSecondsMin,"PastSecondsMax=",PastSecondsMax,"PastBlocksMin=",PastBlocksMin,"PastBlocksMax=",PastBlocksMax)
        return new_bits, new_target

def check_header(header: dict) -> Optional[Blockchain]:
    if type(header) is not dict:
        return None
    with blockchains_lock: chains = list(blockchains.values())
    for b in chains:
        if b.check_header(header):
            return b
    return None


def can_connect(header: dict) -> Optional[Blockchain]:
    with blockchains_lock: chains = list(blockchains.values())
    for b in chains:
        if b.can_connect(header):
            return b
    return None
