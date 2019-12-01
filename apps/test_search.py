from flask import *
from flask_jwt_extended import *
from werkzeug import *
##########################################
from bson.json_util import dumps
from bson.objectid import ObjectId
from datetime import timedelta, datetime
import operator
import math
##########################################
from db_management import *
from global_func import *
import jpype
import tknizer
import time
##########################################
BP = Blueprint('search', __name__)
##########################################
#JAVA 스레드 이동.
jpype.attachThreadToJVM()

def match_score(token1, token2):
	MC = len(set(token1) & set(token2))
	MR = MC / len(token1)
	return MC * (1 + MR + math.floor(MR))

#priority_검색
@BP.route('/priority_search/<int:num>', methods = ['POST'])
@jwt_optional
def priority_search(num):
	search_str = request.form['search']

	print("검색어 :", search_str)

	TIME_LOG = {}

	#######################################################################################
	TITLE_REGEX_time = time.time()
	#검색어로 시작되는 포스트들을 1차 regex 검색!
	title_regex = find_title_regex(g.db, search_str, 0)
	title_regex = list(title_regex)
	TIME_LOG['TITLE_REGEX_time'] = time.time() - TITLE_REGEX_time
	TIME_LOG['TITLE_REGEX_LEN'] = len(title_regex)
	

	######################################################################################
	DEL_SPACE_time = time.time()
	#공백 제거
	del_space_list = search_str.split(' ')
	TIME_LOG['DEL_SPACE_time'] = time.time() - DEL_SPACE_time

	#######################################################################################
	TOKENIZER_time = time.time()
	#토크나이져 작업
	tokenizer_list = tknizer.get_tk(search_str)
	TIME_LOG['tokenizer_list'] = tokenizer_list
	TIME_LOG['TOKENIZER_time'] = time.time() - TOKENIZER_time

	#######################################################################################
	FASTTEXT_time = time.time()
	#FastText를 이용한 유사단어 추출
	ft_similarity_list = []
	for word in tokenizer_list:
		for sim_word in FastText.sim_words(word):
			if sim_word[1] >= 0.7: 
				ft_similarity_list.append(sim_word[0])
			else: break	
	TIME_LOG['FASTTEXT_time'] = time.time() - FASTTEXT_time

	if get_jwt_identity():
		#logging!
		insert_log(g.db, get_jwt_identity(), request.url)

		#USER 정보를 불러온다.
		USER = find_user(g.db, user_id=get_jwt_identity())

		#잘못된 USER 정보(잘못된 Token)일 때
		if USER is None: abort(400)

		#DB search 로깅!
		search_log(g.db, USER['user_id'], search_str, del_space_list, tokenizer_list, ft_similarity_list)

	else:
		#logging!
		insert_log(g.db, request.full_path, request.url)
		#DB search 로깅!
		search_log(g.db, "unknown", search_str, del_space_list, tokenizer_list, ft_similarity_list)		

	#######################################################################################
	AGGREGATE_time = time.time()
	#토크나이져 처리된 리스트를 대상으로 검색하고, aggregate로 ids처리하여 posts 추출
	aggregate_posts = find_aggregate(g.db, tokenizer_list, 0)
	aggregate_posts = list(aggregate_posts)
	TIME_LOG['AGGREGATE_time'] = time.time() - AGGREGATE_time
	TIME_LOG['AGGREGATE_time_len'] = len(aggregate_posts)

	#regex와 aggregate로 뽑힌 포스트를 합친다.
	aggregate_posts += title_regex

	#######################################################################################
	SIMILARITY_time = time.time()
	#검색 키워드와 문서간의 유사도 측정!
	for post in aggregate_posts:
		T1 = match_score(del_space_list, post['title_token'])
		
		if tokenizer_list:
			T2 = match_score(tokenizer_list, set(post['token']+post['tag']))
		else: T2 =0

		if ft_similarity_list:
			T3 = match_score(ft_similarity_list, set(post['token']+post['tag']))
		else: T3 = 0

		post['similarity'] = T1 + T2 + T3
		post['_id'] = str(post['_id'])

		#필요없는 반환 값 삭제
		del post['title_token']
		del post['token']
		del post['tag']
		del post['popularity']
	TIME_LOG['SIMILARITY_time'] = time.time() - SIMILARITY_time

	#######################################################################################
	SORT_time = time.time()
	#구해진 similarity로 내림차순 정렬
	aggregate_posts = sorted(aggregate_posts, key=operator.itemgetter('similarity'), reverse=True)
	TIME_LOG['SORT_time'] = time.time() - SORT_time

	print("Priority) Title regex 시간 :", TIME_LOG['TITLE_REGEX_time'], "( 총 반환 개수 :", TIME_LOG['TITLE_REGEX_LEN'], ")")
	print("Priority) 공백 제거 시간 :", TIME_LOG['DEL_SPACE_time'])
	print("Priority) Tokenizer 분류 시간 :", TIME_LOG['TOKENIZER_time'])
	print("Priority) FastText 유사 단어 추출 시간 :", TIME_LOG['FASTTEXT_time'])
	print("Priority) IDS 정렬 순 최대 상위 10000개 호출 시간 :", TIME_LOG['AGGREGATE_time'], "( 총 반환 개수 :", TIME_LOG['AGGREGATE_time_len'], ")")
	print("Priority)", TIME_LOG['AGGREGATE_time_len'], "개의 문서와 검색어 간의 유사도 측정 시간 : ", TIME_LOG['SIMILARITY_time'])
	print("Priority)", TIME_LOG['AGGREGATE_time_len'], "개의 문서의 similarity정렬 시간 :", TIME_LOG['SORT_time'])
	print("토크나이져 :",TIME_LOG['tokenizer_list'])
	print("#######################################################################################################################")

	#데이터로 들어온 상위 num개만 반환
	return jsonify(
		result = "success",
		search_result = aggregate_posts[:num])

#category_검색
@BP.route('/category_search/<int:type_check>/<int:num>', methods = ['POST'])
@jwt_optional
def category_search(type_check, num):
	TIME_LOG = {}

	#logging!
	if get_jwt_identity():
		insert_log(g.db, get_jwt_identity(), request.url)
	else:
		insert_log(g.db, request.full_path, request.url)

	search_str = request.form['search']

	print("검색어 :", search_str)

	#######################################################################################
	TITLE_REGEX_time = time.time()
	#검색어로 시작되는 포스트들을 1차 regex 검색!
	title_regex = find_title_regex(g.db, search_str, type_check)
	title_regex = list(title_regex)
	TIME_LOG['TITLE_REGEX_time'] = time.time() - TITLE_REGEX_time
	TIME_LOG['TITLE_REGEX_LEN'] = len(title_regex)

	######################################################################################
	DEL_SPACE_time = time.time()
	#공백 제거
	del_space_str = search_str.split(' ')
	TIME_LOG['DEL_SPACE_time'] = time.time() - DEL_SPACE_time

	#######################################################################################
	TOKENIZER_time = time.time()
	#토크나이져 작업
	tokenizer_list = tknizer.get_tk(search_str)
	TIME_LOG['TOKENIZER_time'] = time.time() - TOKENIZER_time

	#######################################################################################
	FASTTEXT_time = time.time()
	#FastText를 이용한 유사단어 추출
	ft_similarity_list = []
	for word in tokenizer_list:
		for sim_word in FastText.sim_words(word):
			if sim_word[1] >= 0.7: 
				ft_similarity_list.append(sim_word[0])
			else: break	
	TIME_LOG['FASTTEXT_time'] = time.time() - FASTTEXT_time

	#######################################################################################
	AGGREGATE_time = time.time()
	aggregate_posts = find_aggregate(g.db, tokenizer_list, type_check)
	aggregate_posts = list(aggregate_posts)
	TIME_LOG['AGGREGATE_time'] = time.time() - AGGREGATE_time
	TIME_LOG['AGGREGATE_time_len'] = len(aggregate_posts)

	#regex와 aggregate로 뽑힌 포스트를 합친다.
	aggregate_posts += title_regex

	#######################################################################################
	SIMILARITY_time = time.time()
	for post in aggregate_posts:
		T1 = match_score(del_space_str, post['title_token'])

		if tokenizer_list:
			T2 = match_score(tokenizer_list, set(post['token']+post['tag']))
		else:
			T2 =0

		if ft_similarity_list:
			T3 = match_score(ft_similarity_list, set(post['token']+post['tag']))
		else:
			T3 = 0

		post['similarity'] = T1 + T2 + T3
		post['_id'] = str(post['_id'])

		#필요없는 반환 값 삭제
		del post['title_token']
		del post['token']
		del post['tag']
		del post['popularity']

	TIME_LOG['SIMILARITY_time'] = time.time() - SIMILARITY_time

	#######################################################################################
	SORT_time = time.time()
	#구해진 similarity로 내림차순 정렬
	aggregate_posts = sorted(aggregate_posts, key=operator.itemgetter('similarity'), reverse=True)
	TIME_LOG['SORT_time'] = time.time() - SORT_time

	print(type_check, "Category) Title regex 시간 :", TIME_LOG['TITLE_REGEX_time'], "( 총 반환 개수 :", TIME_LOG['TITLE_REGEX_LEN'], ")")
	print(type_check, "Category) 공백 제거 시간 :", TIME_LOG['DEL_SPACE_time'])
	print(type_check, "Category) Tokenizer 분류 시간 :", TIME_LOG['TOKENIZER_time'])
	print(type_check, "Category) FastText 유사 단어 추출 시간 :", TIME_LOG['FASTTEXT_time'])
	print(type_check, "Category) IDS 정렬 순 최대 상위 10000개 호출 시간 :", TIME_LOG['AGGREGATE_time'], "( 총 반환 개수 :", TIME_LOG['AGGREGATE_time_len'], ")")
	print(type_check, "Category)", TIME_LOG['AGGREGATE_time_len'], "개의 문서와 검색어 간의 유사도 측정 시간 : ", TIME_LOG['SIMILARITY_time'])
	print(type_check, "Category)", TIME_LOG['AGGREGATE_time_len'], "개의 문서의 similarity정렬 시간 :", TIME_LOG['SORT_time'])
	print("#######################################################################################################################")

	#데이터로 들어온 상위 num개만 반환
	return jsonify(
		result = "success",
		search_result = aggregate_posts[:num])

#domain_검색
@BP.route('/domain_search', methods = ['POST'])
@jwt_optional
def domain_search():
	search_str = request.form['search']

	#토크나이져 작업
	tokenizer_list = tknizer.get_tk(search_str)

	if not tokenizer_list:
		return jsonify(
			result = "success",
			search_result = [])

	#FastText를 이용한 유사단어 추출
	ft_similarity_list = []
	for word in tokenizer_list:
		for sim_word in FastText.sim_words(word):
			if sim_word[1] >= 0.7: 
				ft_similarity_list.append(sim_word[0])
			else: break	


	regex_list = tokenizer_list + ft_similarity_list
	regex_str = "|".join(regex_list)

	search_result = find_domain_title_regex(g.db, search_str)
	search_result = list(search_result)
	result = find_domain_post_regex(g.db, regex_str)

	result = search_result + list(result)

	return jsonify(
		result = "success",
		search_result = result)

#search_log 기록!
def search_logging(db, user_id, original_str, split_list, tokenizer_list, similarity_list):
	
	if user_id:
		USER_search_obj = {}
		USER_search_obj['original'] = original_str
		USER_search_obj['search_split'] = split_list
		USER_search_obj['tokenizer_split'] = tokenizer_list
		USER_search_obj['similarity_split'] = similarity_list
		USER_search_obj['date'] = datetime.now()

		#유저 searching 기록!
		update_user_search_list_push(db, user_id, USER_search_obj)

	#공용 searching 기록!
	insert_search_log(db, user_id, split_list)