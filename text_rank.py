import numpy as np
import pandas as pd
import nltk
import re
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from gensim.models import Word2Vec
from scipy import spatial
import networkx as nx

text='''Mahendra Singh Dhoni (born 7 July 1981), is a former Indian international cricketer who captained the Indian national team in limited-overs formats from 2007 to 2017 and in Test cricket from 2008 to 2014. 
Under his captaincy, India won the inaugural 2007 ICC World Twenty20, the 2010 and 2016 Asia Cups, the 2011 ICC Cricket World Cup and the 2013 ICC Champions Trophy. 
A right-handed middle-order batsman and wicket-keeper, Dhoni is one of the highest run scorers in One Day Internationals (ODIs) with more than 10,000 runs scored and is considered an effective "finisher" in limited-overs formats.
He is widely regarded as one of the greatest wicket-keeper batsmen and captains in the history of the game.
He was also the first wicket-keeper to effect 100 stumpings in ODI cricket.
Dhoni made his ODI debut on 23 December 2004 against Bangladesh, and played his first Test a year later against Sri Lanka. 
He has been the recipient of many awards, including the ICC ODI Player of the Year award in 2008 and 2009 (the first player to win the award twice), the Rajiv Gandhi Khel Ratna award in 2007, the Padma Shri, India's fourth highest civilian honour, in 2009 and the Padma Bhushan, India's third highest civilian honour, in 2018.
Dhoni was named as the captain of the ICC World Test XI in 2009, 2010 and 2013. 
He has also been selected a record 8 times in ICC World ODI XI teams, 5 times as captain. 
The Indian Territorial Army conferred the honorary rank of Lieutenant Colonel to Dhoni on 1 November 2011. 
He is the second Indian cricketer after Kapil Dev to receive this honour.
Dhoni also holds numerous captaincy records such as the most wins by an Indian captain in ODIs and T20Is, and most back-to-back wins by an Indian captain in ODIs. 
He took over the ODI captaincy from Rahul Dravid in 2007 and led the team to its first-ever bilateral ODI series wins in Sri Lanka and New Zealand. 
In June 2013, when India defeated England in the final of the Champions Trophy in England, Dhoni became the first captain to win all three ICC limited-overs trophies (World Cup, Champions Trophy and the World Twenty20). 
After taking up the Test captaincy in 2008, he led the team to series wins in New Zealand and the West Indies, and the Border-Gavaskar Trophy in 2008, 2010 and 2013. 
In 2009, Dhoni also led the Indian team to number one position for the first time in the ICC Test rankings.
In 2013, under Dhoni's captaincy, India became the first team in more than 40 years to whitewash Australia in a Test series. 
In the Indian Premier League, he captained the Chennai Super Kings to victory at the 2010, 2011 and 2018 seasons, along with wins in the 2010 and 2014 editions of Champions League Twenty20. 
In 2011, Time magazine included Dhoni in its annual Time 100 list as one of the "Most Influential People in the World."
Dhoni holds the post of Vice-President of India Cements Ltd., after resigning from Air India. 
India Cements is the owner of the Indian Premier League team Chennai Super Kings, and Dhoni has been its captain since the first IPL season. 
He announced his retirement from Tests on 30 December 2014.
In 2012, SportsPro rated Dhoni as the sixteenth most marketable athlete in the world. 
He is the co-owner of Indian Super League team Chennaiyin FC. 
In June 2015, Forbes ranked Dhoni at 23rd in the list of highest paid athletes in the world, estimating his earnings at US$31 million. 
In 2016, a biopic M.S. Dhoni: The Untold Story was made on his life and his cricket career up to the Indian team's win at the 2011 Cricket World Cup.
MS Dhoni announced his retirement from international cricket on 15 August 2020.
  
  '''

sentences=sent_tokenize(text)

sentences_clean=[re.sub(r'[^\w\s]','',sentence.lower()) for sentence in sentences]
stop_words = stopwords.words('english')
sentence_tokens=[[words for words in sentence.split(' ') if words not in stop_words] for sentence in sentences_clean]

w2v=Word2Vec(sentence_tokens,size=1,min_count=1,iter=1000)
sentence_embeddings=[[w2v[word][0] for word in words] for words in sentence_tokens]
max_len=max([len(tokens) for tokens in sentence_tokens])
sentence_embeddings=[np.pad(embedding,(0,max_len-len(embedding)),'constant') for embedding in sentence_embeddings]

similarity_matrix = np.zeros([len(sentence_tokens), len(sentence_tokens)])
for i,row_embedding in enumerate(sentence_embeddings):
    for j,column_embedding in enumerate(sentence_embeddings):
        similarity_matrix[i][j]=1-spatial.distance.cosine(row_embedding,column_embedding)

nx_graph = nx.from_numpy_array(similarity_matrix)
scores = nx.pagerank(nx_graph)

top_sentence={sentence:scores[index] for index,sentence in enumerate(sentences)}
top=dict(sorted(top_sentence.items(), key=lambda x: x[1], reverse=True)[:10])  

print("\n")

for sent in sentences:
    if sent in top.keys():
        print(sent)