from electrum_sct import auxpow, blockchain, constants
from electrum_sct.util import bfh

from . import SequentialTestCase
from . import TestCaseForTestnet
from . import FAST_TESTS

smartcryptotech_header_37174 = '01010100d681bfa4acb5e0dc772a0099ce069ae4841ee2292ba731a63ac746bde66ddc8a79ad23ebbe11a144734b56d5bba0d0fb9ee68928112eb695a342e74899b3f78138950a4f4a2a241a0000000001000000010000000000000000000000000000000000000000000000000000000000000000ffffffff3907456c696769757303f8a7022cfabe6d6d2d27ea3a0cbe9d4edcecb32f6ed254b2bd017cb1f13258c9fd040b20519cbae41000000000000000ffffffff20abdd2a000000000043410400ffc6890975ea785b450af3d4d0908303969581b3bc9f2b32172312fdd0c2e0e92285856abfc6f5abf6f79572a9084cdaf1678905dc7c00b2aa24368d90454cac283ee709000000001976a9148eafb1970e427d4d6ebb213b737b7dcdc96791e988acf974b706000000001976a91432e9b63db5ade6c81433fc1f3386d2a9d61c5ca388ac31e8c406000000001976a914b8c835af5f431a5b29f02f27f34617fab43f869d88ac5c5c1905000000001976a91438eb0cfbf241ce393845eaab98b03509b1a4f4c988ac12a99406000000001976a914a9e01ae5f2e882d018ca6c9c0b62805f419f678488ac2eafeb0e000000001976a914e5673d0aaa04d7ef76cac33443c4d65f1f9d3abd88acab8c3b06000000001976a914890ee1d550411d3a56f90785f0b50d32422685e588ac2b83040e000000001976a914d6309a28ad26747380adee68c78a82afc2e380b088ac37d85708000000001976a914cac51e198e50f78b352b7543450d4adb19a1ecb588ac7024b209000000001976a9141ba5c1c3c0916014ee18f35b2c8972d974e0c2c688ac042c9e0f000000001976a9149bc7fd00183f8007edb836e54aaa43fa7093564b88ac11a3270d000000001976a914c784d5639cba9cac3ee83b8419d0df127f814dac88ac9e1a0904000000001976a914ad9d837dd996b6f09408c48fb021f47113893e1288acb2d8b804000000001976a914773e6c68a0a90c3fa8d724a8d956d391cb2e780588acfadfa30a000000001976a91465d2028ef9a711679dd0475ee8c063e03f283b9988ac2cc7de04000000001976a914634a731a7cac60d4009e02de89adeba55b9e7c6988acf4f83704000000001976a914432c607e716ce918f4025ecd34e22149a52d66ac88acd0b63904000000001976a91467cec2520fd4a12f815f6b69601a30ba95e4e1d888aceada260b000000001976a91476ea1118754fe1c7bd7e6e5a3bbf0a58bb50793e88acebc87810000000001976a9146284a45230cf59afc7014972809b33fcd697feae88ac4bd1800e000000001976a9141c0320b4b7d9f4462176b099412804a75ce1b0c288acf71ba505000000001976a914220b8d06c0954da6d4434aac55b6478b116f0d6b88ac795db109000000001976a914c3dd52845bfba22107c21501138a0c8b04a0347588ac84e7560e000000001976a9147ac2b007faf68d60460f26884f41630a0c84bb1f88acbb4ec312000000001976a91471556a3df90c4bfe9e3b0dc1d17b96bef721c15088ac5ed1c909000000001976a9142de17c20ad4acd2eb0a6113b16a296e91dbed2e088ac585e1b04000000001976a9145e141e1a4346cfdcf9059a8d53e12fe73d9fc96188ac1400ed09000000001976a9149465fdac29b5c47b99c8d17379d0fc6d99c1e4a688ac93f00f0b000000001976a914cc48bc094901e59d9f696b4d8b5c6045006bd33188ac76bbb70c000000001976a9149eb551c3924ed46408b3616242db21b7fcc7f9a288ac39186f0a000000001976a914959ccd483cd07cb7ab9c63ae088d36833e52a29388ac0000000084db572a0c547f2d33793a50525ff96d90d46ab361f57311112400000000000005e0dd9751b7164f0bd8da996fd31d1944dd28bbba422612ae65512a021473f2f8b0edec19fc4bd2b5e0df0feaf0c35b9eed377a4c17c04bb0e7de170e42dca9c82036c3370630069cc8b763dcc4dff4e8c45d4398927baae42725218eb9c5e90c3641e824664bb1f0c6011f45bdf646049f836104449a87cb47b0a522410c6d3bcb36e428be422a5de15c00b24f0352dd8fc0d9525edf1251218ba638be00854500000000040a0000000000000000000000000000000000000000000000000000000000000002837963a2278915e751bb7f197f196b39e559867e97076564a3e3c7b28ebd65e9720db28e9dc39e9b719e7bf8955c5397701fa07683b2ab05d78932b11b965f50eb6b2eb0dc8cd70c2e6d93a25b679b0cdcbd53670aa435610d1241ccfdb57c0b0000000100000055a7bc918827dbe7d8027781d803f4b418589b7b9fc03e718a03000000000000625a3d6dc4dfb0ab25f450cd202ff3bdb074f2edde1ddb4af5217e10c9dbafb9639a0a4fd7690d1a25aeaa97'

class Test_auxpow(SequentialTestCase):

    # Deserialize the AuxPoW header from SmartCryptoTech block #37,174.
    # This height was chosen because it has large, non-equal lengths of the
    # coinbase and chain Merkle branches.
    def test_deserialize_auxpow_header(self):
        header_bytes = bfh(smartcryptotech_header_37174)
        # We can't pass the real height because it's below a checkpoint, and
        # the deserializer expects ElectrumX to strip checkpointed AuxPoW.
        header = blockchain.deserialize_header(header_bytes, constants.net.max_checkpoint() + 1)
        header_auxpow = header['auxpow']

        self.assertEqual(auxpow.CHAIN_ID, header_auxpow['chain_id'])

        coinbase_tx = header_auxpow['parent_coinbase_tx']
        expected_coinbase_txid = '8a3164be45a621f85318647d425fe9f45837b8e42ec4fdd902d7f64daf61ff4a'
        observed_coinbase_txid = auxpow.fast_txid(coinbase_tx)

        self.assertEqual(expected_coinbase_txid, observed_coinbase_txid)

        coinbase_merkle_branch = header_auxpow['coinbase_merkle_branch']
        self.assertEqual(5, len(coinbase_merkle_branch))
        self.assertEqual('f8f27314022a5165ae122642babb28dd44191dd36f99dad80b4f16b75197dde0', coinbase_merkle_branch[0])
        self.assertEqual('c8a9dc420e17dee7b04bc0174c7a37ed9e5bc3f0ea0fdfe0b5d24bfc19ecedb0', coinbase_merkle_branch[1])
        self.assertEqual('0ce9c5b98e212527e4aa7b9298435dc4e8f4dfc4dc63b7c89c06300637c33620', coinbase_merkle_branch[2])
        self.assertEqual('3b6d0c4122a5b047cb879a440461839f0446f6bd451f01c6f0b14b6624e84136', coinbase_merkle_branch[3])
        self.assertEqual('458500be38a68b215112df5e52d9c08fdd52034fb2005ce15d2a42be28e436cb', coinbase_merkle_branch[4])

        coinbase_merkle_index = header_auxpow['coinbase_merkle_index']
        self.assertEqual(0, coinbase_merkle_index)

        chain_merkle_branch = header_auxpow['chain_merkle_branch']
        self.assertEqual(4, len(chain_merkle_branch))
        self.assertEqual('000000000000000000000000000000000000000000000000000000000000000a', chain_merkle_branch[0])
        self.assertEqual('65bd8eb2c7e3a3646507977e8659e5396b197f197fbb51e7158927a263798302', chain_merkle_branch[1])
        self.assertEqual('5f961bb13289d705abb28376a01f7097535c95f87b9e719b9ec39d8eb20d72e9', chain_merkle_branch[2])
        self.assertEqual('7cb5fdcc41120d6135a40a6753bddc0c9b675ba2936d2e0cd78cdcb02e6beb50', chain_merkle_branch[3])

        chain_merkle_index = header_auxpow['chain_merkle_index']
        self.assertEqual(11, chain_merkle_index)

        expected_parent_hash = '00000000000024111173f561b36ad4906df95f52503a79332d7f540c2a57db84'
        observed_parent_hash = blockchain.hash_header(header_auxpow['parent_header'])
        self.assertEqual(expected_parent_hash, observed_parent_hash)

        expected_parent_header = blockchain.deserialize_header(bfh('0100000055a7bc918827dbe7d8027781d803f4b418589b7b9fc03e718a03000000000000625a3d6dc4dfb0ab25f450cd202ff3bdb074f2edde1ddb4af5217e10c9dbafb9639a0a4fd7690d1a25aeaa97'), 1)
        expected_parent_merkle_root = expected_parent_header['merkle_root']
        observed_parent_merkle_root = header_auxpow['parent_header']['merkle_root']
        self.assertEqual(expected_parent_merkle_root, observed_parent_merkle_root)

