#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import numpy
import theano
import theanolm
from filetypes import TextFileType

def rescore_nbest(input_file, dictionary, scorer, output_file):
    for line in input_file:
        fields = line.split()
        
        words = fields[3:]
        words.append('<sb>')
        
        word_ids = dictionary.words_to_ids(words)
        word_ids = numpy.array([[x] for x in word_ids]).astype('int64')
        
        probs = dictionary.words_to_probs(words)
        probs = numpy.array([[x] for x in probs]).astype('float32')
        
        lm_score = scorer.score_sentence(word_ids, probs)
        fields[1] = str(lm_score)
        output_file.write(' '.join(fields) + '\n')

parser = argparse.ArgumentParser()

argument_group = parser.add_argument_group("files")
argument_group.add_argument(
    'model_path', metavar='MODEL', type=str,
    help='path where the best model state will be saved in numpy .npz format')
argument_group.add_argument(
    'input_file', metavar='INPUT', type=TextFileType('r'),
    help='text or .gz file containing text or n-best list to be scored (one sentence per line)')
argument_group.add_argument(
    'dictionary_file', metavar='DICTIONARY', type=TextFileType('r'),
    help='text or .gz file containing word list (one word per line) or word to class ID mappings (word and ID per line)')
argument_group.add_argument(
    '--input-format', metavar='FORMAT', type=str, default='text',
    help='input text format, one of "text" (one sentence per line, default), "srilm-nbest" (n-best list containing "ascore lscore nwords w1 w2 w3 ..." on each line)')
argument_group.add_argument(
    '--dictionary-format', metavar='FORMAT', type=str, default='words',
    help='dictionary format, one of "words" (one word per line, default), "classes" (word and class ID per line), "srilm-classes" (class name, membership probability, and word per line)')
argument_group.add_argument(
    '--output-file', metavar='OUTPUT', type=TextFileType('w'), default='-',
    help='where to write the score or rescored n-best list (default stdout)')

args = parser.parse_args()

state = numpy.load(args.model_path)

print("Reading dictionary.")
sys.stdout.flush()
dictionary = theanolm.Dictionary(args.dictionary_file, args.dictionary_format)
print("Number of words in vocabulary:", dictionary.num_words())
print("Number of word classes:", dictionary.num_classes())

validation_iter = theanolm.BatchIterator(
    args.input_file,
    dictionary,
    batch_size=1,
    max_sequence_length=None)

print("Building neural network.")
sys.stdout.flush()
rnnlm = theanolm.RNNLM(
    dictionary,
    state['rnnlm_word_projection_dim'],
    state['rnnlm_hidden_layer_type'],
    state['rnnlm_hidden_layer_size'])
print("Restoring neural network state.")
rnnlm.set_state(state)

print("Building text scorer.")
sys.stdout.flush()
scorer = theanolm.TextScorer(rnnlm)

if args.input_format == 'text':
    args.output_file.write("Average sentence negative log probability: %f\n" % \
        scorer.negative_log_probability(validation_iter))
elif args.input_format == 'srilm-nbest':
    rescore_nbest(args.input_file, dictionary, scorer, args.output_file)
