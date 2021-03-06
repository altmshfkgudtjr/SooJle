from flask import *
from flask_jwt_extended import *
from werkzeug import *
from bson.json_util import dumps
from bson.objectid import ObjectId
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from pprint import pprint
##########################################
from db_management import *
from global_func import *
import jpype
import tknizer
##########################################
from variable import *


#BluePrint
BP = Blueprint('analysis', __name__)


#실시간 검색서 순위 반환
@BP.route('/get_search_realtime')
def get_search_realtime():
	result = find_search_realtime(g.db)
	result = result[0]

	return jsonify(
			result = "success",
			search_realtime = result['real_time'][:SJ_REALTIME_RETURN_LIMIT]
		)

#log) 시간대 반환 (date는 한개씩만 사용 가능, limit 설정!)
@BP.route('/get_log_date/<int:months>/<int:days>/<int:hours>/<int:limit>')
def get_log_date(months, days, hours, limit):
	#시간별로 로그 반환!
	if months != 0 and months <= 6:
		date = datetime.now() - relativedelta(months = months)
	elif days != 0 and days <= 7:
		date = datetime.now() - timedelta(days = days)
	elif hours != 0 and hours <= 24:
		date = datetime.now() - timedelta(hours = hours)
	else:
		return jsonify(result = "try again")

	result = find_date_log(g.db, date, limit)
	result = list(result)

	return jsonify(
		result = "success",
		log = result
	)

#log) 특정 user 반환
@BP.route('/get_log_user/<string:user_id>/<int:limit>')
def get_log_user(user_id, limit):
	result = find_user_log(g.db, user_id, limit)
	result = list(result)

	return jsonify(
		result = "success",
		log = result
	)
	
#log) 특정 user, 시간별 반환
@BP.route('/get_log_user_date/<string:user_id>/<int:months>/<int:days>/<int:hours>/<int:limit>')
def get_log_user_date(user_id, months, days, hours, limit):
	#시간별로 로그 반환!
	if months != 0 and months <= 6:
		date = datetime.now() - relativedelta(months = months)
	elif days != 0 and days <= 7:
		date = datetime.now() - timedelta(days = days)
	elif hours != 0 and hours <= 24:
		date = datetime.now() - timedelta(hours = hours)
	else:
		return jsonify(result = "try again")

	result = find_user_date_log(g.db, user_id, date, limit)
	result = list(result)

	return jsonify(
		result = "success",
		log = result)

#입력된 str을 fasttext로 유사한 단어를 추출 해주는 API (연관검색어)
@BP.route('/get_similarity_words', methods = ['POST'])
def simulation_fastext():
	input_str = request.form['search']

	tokenizer_list = tknizer.get_tk(input_str)
	
	result = {}
	for word in tokenizer_list:
		similarity_list = []
		for sim_word in FastText.sim_words(word):
			temp = {}
			if sim_word[1] >= SJ_FASTTEXT_SIM_PERCENT: 
				temp[sim_word[0]] = sim_word[1]
				similarity_list.append(temp)
			else: break	
		result[word] = similarity_list

	return jsonify(
		result = "success",
		similarity_words = result)

#통계 통합형 반환
@BP.route('/get_analysis')
def get_analysis():
	result = {}

	#총 검색 갯수
	result['search_count'] = find_variable(g.db, 'total_search_cnt')
	
	#소통 수 반환 (하루 평균 기준)
	result['communication_avg'] = find_variable(g.db, 'communication_avg')
	
	#총 DB posts 갯수
	result['posts_count'] = find_variable(g.db, 'total_posts_cnt')
	
	#오늘 방문자 수
	result['today_visitor'] = find_today_visitor_count(g.db)

	#총 방문자 수
	result['total_visitor'] = find_variable(g.db, 'total_visitor')

	#하루 평균 방문자 수
	result['day_avg_visitor'] = find_variable(g.db, 'day_avg_visitor')

	#하루 최고 방문자 수
	result['highest_day_visitor'] = find_variable(g.db, 'highest_visitor')

	#전체 게시글 조회수
	result['total_view'] = find_variable(g.db, 'total_view')

	#전체 게시글 좋아요 수
	result['total_fav'] = find_variable(g.db, 'total_fav')

	return jsonify(
		result = "success",
		analysis = result
	)

#매일 기록되는 통계 반환 API (몇일 전 버전)
@BP.route('/get_everyday_analysis_days_ago/<int:days>')
def get_everyday_analysis_days_ago(days):
	today_year = datetime.today().year
	today_month = datetime.today().month
	today_day = datetime.today().day
	
	date = datetime(today_year, today_month, today_day) - timedelta(days = 2)
	
	result = find_everyday_analysis_days(g.db, date)
	result = list(result)

	return jsonify(
		result = "success",
		analysis = result
	)

#매일 기록되는 통계 반환 API (특정 날짜)
@BP.route('/get_everyday_analysis_specific_days/<int:year>/<int:month>/<int:day>')
def get_everyday_analysis_specific_days(year, month, day):
	date = datetime.date(year, month, day)

	result = find_everyday_analysis_specific_day(g.db, date)
	result = list(result)

	return jsonify(
		result = "success",
		analysis = result
	)

#무슨 디바이스로 접속했는지 기록용 API
@BP.route('/insert_device/<string:device>')
def insert_device(device):
	if device == 'device_pc' or device == 'device_tablet' or device == 'device_mobile':
		result = update_variable_inc(g.db, device, 1)

	#잘못된 디바이스가 들어왔을 때!, Bad request 핸들러 반환
	else: abort(400)

	return jsonify(
		result = result
	)

#무슨 디바이스로 접속했는지 기록용 API
@BP.route('/get_device')
def get_device():
	PC = find_variable(g.db, 'device_pc')
	TABLET = find_variable(g.db, 'device_tablet')
	MOBILE = find_variable(g.db, 'device_mobile')

	return jsonify(
		result = "success",
		pc = PC,
		tablet = TABLET,
		mobile = MOBILE
	)

