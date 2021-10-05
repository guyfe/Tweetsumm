from typing import List
import csv
import json
import argparse


class Turn():
    def __init__(self, is_agent : bool, sentences : List[str]):
        self._is_agent = is_agent
        self.sentences = sentences

    def is_agent(self):
        return self._is_agent

    def get_sentences(self):
        return self.sentences

    def get_json(self) -> json:
        result = {
            'is_agent' : self.is_agent(),
            'sentences' : self.sentences
        }
        return json.dumps(result)

    def __str__(self):
        return ('Agent:\t' if self.is_agent() else 'Customer:\t')  + ' '.join(self.sentences)


class Dialog():
    def __init__(self, dialog_id: str, turns: List[Turn]):
        self.dialog_id = dialog_id
        self.turns = turns

    def get_dialog_id(self) -> str:
        return self.dialog_id

    def get_turns(self) -> List[Turn]:
        return self.turns

    def get_json(self) -> json:
        turn_list = [json.loads(turn.get_json()) for turn in self.turns]
        result = {
            'dialog_id' : self.dialog_id,
            'turns' : turn_list
        }
        return json.dumps(result)

    def __str__(self):
        result = self.dialog_id + '\n'
        for turn in self.turns :
            result += '\t' + str(turn) + '\n'
        return result


class DialogWithSummaries():
    def __init__(self, dialog_id: str, turns: List[Turn],
                 extractive_summaries: List[List[Turn]],
                 abstractive_summaries: List[List[str]]):
        self.dialog = Dialog(dialog_id, turns)
        self.extractive_summaries = extractive_summaries
        self.abstractive_summaries = abstractive_summaries

    def get_dialog(self) -> Dialog:
        return self.dialog

    def get_extractive_summaries(self) -> List[List[Turn]]:
        return self.extractive_summaries

    def get_abstractive_summaries(self) -> List[List[str]]:
        return self.abstractive_summaries

    def get_json(self) -> json:
        dialog = json.loads(self.dialog.get_json())
        extractive_summaries_to_json = list()
        for summ in self.extractive_summaries:
            summ_json = [json.loads(turn.get_json()) for turn in summ]
            extractive_summaries_to_json.append(summ_json)
        abstractive_summaries_to_json = list()
        for summ in self.abstractive_summaries:
            abst_json = [txt for txt in summ ]
            abstractive_summaries_to_json.append(abst_json)

        result = {
            'dialog' : dialog,
            'summaries' : {
                'extractive_summaries' : extractive_summaries_to_json,
                'abstractive_summaries' : abstractive_summaries_to_json

            }
        }

        return json.dumps(result)

    def __str__(self):
        result = str(self.dialog)
        result += '\n'
        # Extractive summaries:
        result += 'Extractive summaries:\n'
        result += '=-=-=-=-=-=-=-=-=-=-=\n'
        for cnt,extractive_summary in enumerate(self.extractive_summaries):
            result += ('{0}:\n'.format(cnt))
            for turn in extractive_summary:
                result += '\t' + str(turn) +'\n'
            result += '\n'

        # Abstractive summaries:
        result += 'Abstractive summaries:\n'
        result += '=-=-=-=-=-=-=-=-=-=-=\n'
        for cnt,abstractive_summary in enumerate(self.abstractive_summaries):
            result += ('{0}:\n'.format(cnt))
            result += '\t' + ' '.join(abstractive_summary) +'\n'
            result += '\n'
        return result


class TweetSumProcessor():
    def __init__(self, path_to_twitter_kaggle_file):
        self.tweet_id_to_content = dict()
        with open(path_to_twitter_kaggle_file) as f:
            csv_reader = csv.reader(f)
            # We skip header
            next(csv_reader)
            for line in csv_reader:
                tweet_id = str(line[0])
                in_bound = line[2]
                text = line[4]
                self.tweet_id_to_content[tweet_id] = (in_bound, text)

    def __get_turn(self, tweet_id : str, sentence_offsets : List[dict]) -> Turn:
        content = self.tweet_id_to_content[str(tweet_id)]
        in_bound = content[0]
        text = content[1]
        sentences = list()
        for offset in sentence_offsets:
            start, end = offset.replace('[', '').replace(']', '').split(',')
            sentence = text[int(start):int(end)]
            sentences.append(sentence)
        turn = Turn(is_agent=('FALSE' == str(in_bound).upper()), sentences=sentences)

        return turn

    def __get_turns(self, tweet_ids_sentence_offsets: List[dict]) -> List[Turn]:
        turns = list()
        for tweet_id_sentence_offset in tweet_ids_sentence_offsets :
            tweet_id = tweet_id_sentence_offset['tweet_id']
            offsets = tweet_id_sentence_offset['sentence_offsets']

            turns.append(self.__get_turn(tweet_id, offsets))

        return turns

    def __get_extractive_summaries(self, annotations) -> List[List[Turn]]:
        extractive_summaries = list()
        for annotation in annotations:
            if 'extractive' in annotation.keys():
                extractive_summary = list()
                extractive_annotation = annotation['extractive']
                if extractive_annotation :
                    for sentence in extractive_annotation :
                        tweet_id = sentence['tweet_id']
                        offset = sentence['sentence_offset']
                        turn = self.__get_turn(tweet_id, [offset])
                        extractive_summary.append(turn)
                    extractive_summaries.append(extractive_summary)

        return extractive_summaries

    @staticmethod
    def __get_abstractive_summaries(annotations) -> List[List[str]]:
        summaries = list()
        for annotation in annotations:
            if 'abstractive' in annotation.keys():
                abstractive_summary = annotation['abstractive']
                summaries.append(abstractive_summary)
        return summaries

    def get_dialog_with_summaries(self, tweet_sum_lines: List[str]) -> List[DialogWithSummaries]:
        result = list()

        for tweet_sum_line in tweet_sum_lines:
            tweet_sum_dict = json.loads(tweet_sum_line)
            conversation_id = tweet_sum_dict['conversation_id']
            tweet_ids_sentence_offsets = tweet_sum_dict['tweet_ids_sentence_offset']
            annotations = tweet_sum_dict['annotations']

            turns = self.__get_turns(tweet_ids_sentence_offsets)
            extractive_summaries = self.__get_extractive_summaries(annotations)
            abstractive_summaries = self.__get_abstractive_summaries(annotations)

            dialog_with_summaries = DialogWithSummaries(dialog_id=conversation_id,
                                                        turns=turns,
                                                        extractive_summaries=extractive_summaries,
                                                        abstractive_summaries=abstractive_summaries)
            result.append(dialog_with_summaries)
        return result

