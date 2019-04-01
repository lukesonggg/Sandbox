#  encoder

from __future__ import division

import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence as pack
from torch.nn.utils.rnn import pad_packed_sequence as unpack

from sandbox.utils.misc import aeq


class EncoderBase(nn.Module):
    """
    Base encoder class. Specifies the interface used by different encoder types
    and required by :obj:`sandbox.network.models.NMTModel`.

    .. mermaid::

       graph BT
          A[Input]
          subgraph RNN
            C[Pos 1]
            D[Pos 2]
            E[Pos N]
          end
          F[Memory_Bank]
          G[Final]
          A-->C
          A-->D
          A-->E
          C-->F
          D-->F
          E-->F
          E-->G
    """

    def _check_args(self, src, lengths=None, hidden=None):
        _, n_batch, _ = src.size()
        if lengths is not None:
            n_batch_, = lengths.size()
            aeq(n_batch, n_batch_)

    def forward(self, src, lengths=None):
        """
        Args:
            src (:obj:`LongTensor`):
               padded sequences of sparse indices `[src_len x batch x nfeat]`
            lengths (:obj:`LongTensor`): length of each sequence `[batch]`


        Returns:
            (tuple of :obj:`FloatTensor`, :obj:`FloatTensor`):
                * final encoder state, used to initialize decoder
                * memory bank for attention, `[src_len x batch x hidden]`
        """
        raise NotImplementedError

# vanilla rnn encoder, supports RNN|lstm
class RNNEncoder(EncoderBase):
    def __init__(self, rnn_type, hidden_size, n_layers, dropout, embedding=None):
        super().__init__()
        self.no_pack_padded_seq = False

        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.dropout = dropout

        assert embedding != None
        self.embedding = embedding
        
        self.rnn = getattr(nn, rnn_type)(self.embedding.embedding_size, hidden_size, n_layers, dropout=dropout)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, src, lengths=None):

        self._check_args(src, lengths)

        #src = [src sent len, batch size]
        
        embedded = self.embedding(src)
        packed_emb = embedded
        if lengths is not None and not self.no_pack_padded_seq:
            # Lengths data is wrapped inside a Tensor.
            lengths = lengths.view(-1).tolist()
            packed_emb = pack(embedded, lengths)
        
        #embedded = [src sent len, batch size, emb dim]
        
        memory_bank, encoder_final = self.rnn(packed_emb)
        
        #outputs = [src sent len, batch size, hid dim * n directions]
        #hidden = [n layers * n directions, batch size, hid dim]
        #cell = [n layers * n directions, batch size, hid dim]
        
        #outputs are always from the top hidden layer

        if lengths is not None and not self.no_pack_padded_seq:
            memory_bank = unpack(memory_bank)[0]
        
        return encoder_final, memory_bank