# Nuthouse01 - 06/10/2020 - v4.08
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

from time import time

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import _translation_tools as translation_tools
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import _translation_tools as translation_tools
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = translation_tools = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# by default, respect existing english names if they exist and are latin-only
# if this is set False then local translate will supercede the existing en name result
PREFER_EXISTING_ENGLISH_NAME = True


# MikuMikuDance can display JP characters just fine in the "model info" popup when you load a model
# also I've seen one or two models that have the JP model info blank and all important info in the EN model info
# so I decided to default to not translating the model info section, only copy JP->EN if EN is blank
# if this is true it will try to translate the model info with exactly the same logic as all other fields
TRANSLATE_MODEL_COMMENT = False


# if this is true, accept whatever Google trans returns, even if it has bad chars still in it
# if this is false, and Google trans returns something with bad chars in it, retain the previous EN value
ACCEPT_INCOMPLETE_RESULT = True


# sometimes chinese translation gives better results than japanese translation
# when false, force input to be interpreted as Japanese. When true, autodetect input language.
GOOGLE_AUTODETECT_LANGUAGE = True


# when this is true, it doesn't even attempt online translation. this way you can kinda run the script when
# you run into google's soft-ban.
DISABLE_INTERNET_TRANSLATE = False


# to reduce the number of translation requests, a list of strings is joined into one string broken by newlines
# that counts as "fewer requests" for google's API
# tho in testing, sometimes translations produce different results if on their own vs in a newline list... oh well
# or sometimes they lose newlines during translation
# more lines per request = riskier, but uses less of your transaction budget
TRANSLATE_MAX_LINES_PER_REQUEST = 15
# how many requests are permitted per timeframe, to avoid the lockout
# true limit is ~100 so enforce limit of 80 just to be safe
TRANSLATE_BUDGET_MAX_REQUESTS = 80
# how long (hours) is the timeframe to protect
# true timeframe is ~1 hr so enforce limit of ~1.2hr just to be safe
TRANSLATE_BUDGET_TIMEFRAME = 1.2



# don't touch this
_DISABLE_INTERNET_TRANSLATE = False
# set up the acutal translator libraries & objects
jp_to_en_google = None
try:
	import googletrans
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import primary translation provider library 'googletrans'")
	print("Please install this library with 'pip install googletrans'")
	googletrans = None
	DISABLE_INTERNET_TRANSLATE = True


category_dict = {0: "header", 4: "mat", 5: "bone", 6: "morph", 7: "disp"}
type_dict = {-1: "FAIL", 0: "good", 1: "copyJP", 2: "exact", 3: "piece", 4: "google"}
specificdict_dict = {0:None, 4:None,
					 5:translation_tools.bone_dict,
					 6:translation_tools.morph_dict,
					 7:translation_tools.frame_dict}


"""
translation plan

goal: translate everything accurately & efficiently, but also record what layer each translation came from.
user can tolerate ~1sec delay: code efficiency/speed is far less important than code cleanliness, compactness, readability
want to efficiently minimize # of Google Translate API calls, to avoid hitting the lockout
0 input already good > 1 copy JP > 2 category-specific exact match > 3 local picewise trans > 4 google piecewise trans > -1 fail
"""



################################################################################################################

def check_translate_budget(num_proposed: int) -> bool:
	"""
	Goal: block translations that would trigger the lockout.
	Create & maintain a persistient file that contains timestamps and # of requests, to know if my proposed number will
	exceed the budget. If it would still be under budget, then update the log assuming that the proposed requests will
	happen.
	options: TRANSLATE_BUDGET_MAX_REQUESTS, TRANSLATE_BUDGET_TIMEFRAME
	:param num_proposed: number of times I want to contact the google API
	:return: bool True = go ahead, False = stop
	"""
	
	# first, get path to persistient storage file, also creates an empty file if it doesn't exist
	recordpath = core.get_persistient_storage_path("translate_record.txt")
	# then read the file into memory, quietly
	record = core.read_txt_to_rawlist(recordpath, quiet=True)
	# discard all request records that are older than <timeframe>
	now = time()
	i = 0
	while i < len(record):
		if (now - record[i][0]) > (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60):
			# print("debug: discard", record[i])
			record.pop(i)
		else:
			i += 1
	# then interpret the file: how many requests happened in the past <timeframe>
	requests_in_timeframe = sum([entry[1] for entry in record])
	core.MY_PRINT_FUNC("You have used {} / {} translation requests within the last {:.4} hrs".format(
		int(requests_in_timeframe), int(TRANSLATE_BUDGET_MAX_REQUESTS), TRANSLATE_BUDGET_TIMEFRAME))
	# make the decision
	if (requests_in_timeframe + num_proposed) <= TRANSLATE_BUDGET_MAX_REQUESTS:
		# this many translations is OK! go ahead!
		# write this transaction into the record
		record.append([now, num_proposed])
		core.write_rawlist_to_txt(recordpath, record, quiet=True)
		return True
	else:
		# cannot do the translate, this would exceed the budget
		# bonus value: how long until enough records expire that i can do this?
		if num_proposed >= TRANSLATE_BUDGET_MAX_REQUESTS:
			core.MY_PRINT_FUNC("BUDGET: you cannot make this many requests all at once")
		else:
			to_be_popped = 0
			idx = 0
			for idx in range(len(record)):
				to_be_popped += record[idx][1]
				if (requests_in_timeframe + num_proposed - to_be_popped) <= TRANSLATE_BUDGET_MAX_REQUESTS:
					break
			# when record[idx] becomes too old, then the current proposed number will be okay
			waittime = record[idx][0] + (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60) - now
			# convert seconds to minutes
			waittime = round(waittime / 60)
			core.MY_PRINT_FUNC("BUDGET: you must wait %d minutes before you can do %d more translation requests with Google" % (waittime, num_proposed))
		
		return False
	
################################################################################################################

def my_list_partition(l, condition):
	"""
	Split one list into two NEW lists based on a condition. Kinda like a list comprehension but it produces 2 results.
	:param l: the list to be split in two
	:param condition: lambda function that returns true or false
	:return: tuple of lists, (list_lambda_true, list_lambda_false)
	"""
	list_where_true = []
	list_where_false = []
	for iiiii in l:
		if condition(iiiii):
			list_where_true.append(iiiii)
		else:
			list_where_false.append(iiiii)
	return list_where_true, list_where_false

def combine_translate_requests(jp_list: list) -> list:
	"""
	Split/join a massive list of items to translate into fewer requests which each contain many separated by newlines.
	options: TRANSLATE_MAX_LINES_PER_REQUEST.
	"""
	retme = []
	start_idx = 0
	while start_idx < len(jp_list):
		sub_list = jp_list[start_idx:start_idx + TRANSLATE_MAX_LINES_PER_REQUEST]
		bigstr = "\n".join(sub_list)
		retme.append(bigstr)
		start_idx += TRANSLATE_MAX_LINES_PER_REQUEST
	return retme

def unpack_translate_requests(list_after: list) -> list:
	"""
	Opposite of combine_translate_requests().
	"""
	retme = []
	for after in list_after:
		results = after.split("\n")
		retme.extend(results)
	return retme

def _single_google_translate(jp_str: str) -> str:
	"""
	Actually send a single string to Google API for translation, unless internet trans is disabled.
	Options: _DISABLE_INTERNET_TRANSLATE and GOOGLE_AUTODETECT_LANGUAGE.
	:param jp_str: JP string to be translated
	:return: usually english-translated result
	"""
	if _DISABLE_INTERNET_TRANSLATE:
		return jp_str
	try:
		# acutally send a single string to Google for translation
		if GOOGLE_AUTODETECT_LANGUAGE:
			r = jp_to_en_google.translate(jp_str, dest="en")  # auto
		else:
			r = jp_to_en_google.translate(jp_str, dest="en", src="ja")  # jap
		return r.text
	except ConnectionError as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("Check your internet connection?")
		raise RuntimeError()
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		if hasattr(e, "doc"):
			core.MY_PRINT_FUNC("Response from Google:")
			core.MY_PRINT_FUNC(e.doc.split("\n")[7])
			core.MY_PRINT_FUNC(e.doc.split("\n")[9])
		core.MY_PRINT_FUNC("Google API has rejected the translate request")
		core.MY_PRINT_FUNC("This is probably due to too many translate requests too quickly")
		core.MY_PRINT_FUNC("Strangely, this lockout does NOT prevent you from using Google Translate thru your web browser. So go use that instead.")
		core.MY_PRINT_FUNC("Get a VPN or try again in about 1 day (TODO: CONFIRM LOCKOUT TIME)")
		raise RuntimeError()

################################################################################################################

def easy_translate(jp, en, specific_dict=None):
	"""
	attempt to translate a string using the 'easy' methods.
	0: input already good.
	1: copied from JP.
	2: exact match in specific dict.
	return new name + the type of translation that succeeded or -1.
	options: PREFER_EXISTING_ENGLISH_NAME will cause mode 0 to be checked here.
	"""
	# first, if en name is already good (not blank and not JP), just keep it
	if PREFER_EXISTING_ENGLISH_NAME and en and not en.isspace() and not translation_tools.needs_translate(en):
		return en, 0
	
	# do pretranslate here: better for exact matching against morphs that have sad/sad_L/sad_R etc
	# TODO: save the pretranslate results so I don't need to do it twice more? meh, it runs just fine
	indent, body, suffix = translation_tools.pre_translate(jp)
	
	# second, jp name is already good english, copy jp name -> en name
	if body and not body.isspace() and not translation_tools.needs_translate(body):
		return (indent + body + suffix), 1
	
	# third, see if this name is an exact match in the specific dict for this specific type
	if specific_dict is not None and body in specific_dict:
		return (indent + specific_dict[body] + suffix), 2
	
	# if none of these pass, return nothing & type -1 to signfiy it is still in progress
	return "", -1

def google_translate(in_list, strategy=1):
	"""
	Take a list of strings & get them all translated by asking Google. Can use per-line strategy or new 'chunkwise' strategy.
	:param in_list: list of JP or partially JP strings
	:param strategy: 0=old per-line strategy, 1=new chunkwise strategy, 2=auto choose whichever needs less Google traffic
	:return: list of strings almost guaranteed to be pure EN, but sometimes CN chars sneak in and confuse the translator
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	
	use_chunk_strat = True if strategy == 1 else False
	
	# in_list -> pretrans
	# in_list -> jp_chunks -> jp_chunks_combined -> results_combined -> results
	# jp_chunks + results -> google_dict
	# pretrans + google_dict -> outlist
	
	# 1. pre-translate to take care of common tasks
	indents, bodies, suffixes = translation_tools.pre_translate(in_list)
	
	# 2. identify chunks
	jp_chunks = set()
	# idea: walk & look for transition from en to jp?
	for s in bodies:  # for every string to translate,
		rstart = 0
		prev_islatin = True
		is_latin = True
		for i in range(len(s)):  # walk along its length one char at a time,
			# use "is_jp" here and not "is_latin" so chunks are defined to be only actual JP stuff and not unicode whatevers
			is_latin = not translation_tools.is_jp(s[i])
			# if char WAS latin but now is NOT latin, then this is the start of a range.
			if prev_islatin and not is_latin:
				rstart = i
			# if it was jp and is now latin, then this is the end of a range (not including here). save it!
			elif is_latin and not prev_islatin:
				jp_chunks.add(s[rstart:i])
			prev_islatin = is_latin
		# now outside the loop... if i ended with a non-latin char, grab the final range & add that too
		if not is_latin:
			jp_chunks.add(s[rstart:len(s)])
	
	# 3. organize/collect chunks
	jp_chunks = list(jp_chunks)
	localtrans_dict = dict()
	# remove the chunks that can already be translated
	# chunks are guaranteed to NOT be part of compound words, probably. so any exact matches with my words-dict should be valid!
	jp_chunks_localtrans = translation_tools.piecewise_translate(jp_chunks, translation_tools.words_dict)
	# results are chunk+trans: split into (where trans failed) (where trans passed)
	# use "is_jp"->fail and not "needs_translate" so I am only sending actual JP stuff to Google and not unicode arrows or whatever
	trans_fail, trans_pass = my_list_partition(zip(jp_chunks, jp_chunks_localtrans), lambda x: translation_tools.is_jp(x[1]))
	for chunk, trans in trans_pass:  # add dict entries for the ones that passed
		localtrans_dict[chunk] = trans
	jp_chunks = [j[0] for j in trans_fail]  # rebuild the jp_chunks list for the ones that failed
	
	# 4. combine them into fewer requests
	jp_chunks_combined = combine_translate_requests(jp_chunks)
	pretrans_combined = combine_translate_requests(bodies)
	if strategy == 2:    use_chunk_strat = (len(jp_chunks_combined) < len(pretrans_combined))
	
	# 5. check the translate budget to see if I can afford this
	num_calls = len(jp_chunks_combined) if use_chunk_strat else len(pretrans_combined)
	global _DISABLE_INTERNET_TRANSLATE
	if check_translate_budget(num_calls) and not _DISABLE_INTERNET_TRANSLATE:
		core.MY_PRINT_FUNC("Making %d requests to Google Translate web API..." % num_calls)
	else:
		# no need to print failing statement, the function already does
		core.MY_PRINT_FUNC("Just copying JP -> EN while Google Translate is disabled")
		_DISABLE_INTERNET_TRANSLATE = True
	# don't quit early, run thru the same full structure & eventually return a copy of the JP names
	
	# 6. send chunks to Google
	results_combined = []
	if use_chunk_strat:
		for d, combined in enumerate(jp_chunks_combined):
			core.print_progress_oneline(d / len(jp_chunks_combined))
			r = _single_google_translate(combined)
			results_combined.append(r)
		
		# 7. assemble Google responses & re-associate with the chunks
		results = unpack_translate_requests(results_combined)  # unpack so they align once more
		google_dict = dict(zip(jp_chunks, results))  # build dict
		
		print("#items=", len(in_list), "#chunks=", len(jp_chunks), "#requests=", len(jp_chunks_combined))
		print(google_dict)
		
		google_dict.update(localtrans_dict)  # add dict entries from things that succeeded localtrans
		# dict->list->sort->dict: sort the longest chunks first, VERY CRITICAL so things don't get undershadowed!!!
		google_dict = dict(sorted(list(google_dict.items()), reverse=True, key=lambda x: len(x[0])))
		
		# 8. piecewise translate using newly created dict
		outlist = translation_tools.piecewise_translate(bodies, google_dict)
	else:
		# old style: just translate the strings directly and return their results
		for d, combined in enumerate(pretrans_combined):
			core.print_progress_oneline(d / len(pretrans_combined))
			r = _single_google_translate(combined)
			results_combined.append(r)
		outlist = unpack_translate_requests(results_combined)
	
	# last, reattach the indents and suffixes
	outlist = [i + b + s for i, b, s in zip(indents, outlist, suffixes)]
	
	# return
	if input_is_str: return outlist[0]  # if original input was a single string, then de-listify
	else:			return outlist  # otherwise return as a list

################################################################################################################


helptext = '''====================
translate_to_english:
This tool fills out empty EN names in a PMX model with translated versions of the JP names.
It tries to do some intelligent piecewise translation using a local dictionary but goes to Google Translate if that fails.
Machine translation is never 100% reliable, so this is only a stopgap measure to eliminate all the 'Null_##'s and wrongly-encoded garbage and make it easier to use in MMD. A bad translation is better than none at all!
Also, Google Translate only permits ~100 requests per hour, if you exceed this rate you will be locked out for 24 hours (TODO: CONFIRM LOCKOUT TIME)
But my script has a built in limiter that will prevent you from translating if you would exceed the 100-per-hr limit.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_translate.pmx"
'''


def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx


# class with named fields is a bit better than just a list of lists with prescribed order
class translate_entry:
	def __init__(self, jp_old, en_old, cat_id, idx, en_new, trans_type):
		self.jp_old = jp_old
		self.en_old = en_old
		self.cat_id = cat_id		# aka category aka type
		self.idx = idx				# aka which bone
		self.en_new = en_new
		self.trans_type = trans_type
	def __str__(self):
		s = "jp_old:%s en_old:%s cat_id:%d idx:%d en_new:%s trans_type:%d" % \
			(self.jp_old, self.en_old, self.cat_id, self.idx, self.en_new, self.trans_type)
		return s


def translate_to_english(pmx, moreinfo=False):
	# for each category,
	# 	for each name,
	# 		check for type 0/1/2 (already good, copy JP, exact match in special dict)
	# 		create translate_entry regardless what happens
	# do same thing for model name
	# then for all that didn't get successfully translated,
	# do bulk local piecewise translate: list(str) -> list(str)
	# then for all that didn't get successfully translated,
	# do bulk google piecewise translate: list(str) -> list(str)
	# then sort the results
	# then format & print the results

	
	# step zero: set up the translator thingy
	global jp_to_en_google
	global _DISABLE_INTERNET_TRANSLATE
	_DISABLE_INTERNET_TRANSLATE = DISABLE_INTERNET_TRANSLATE  # create a second global var so I can reset this one to default each time it runs
	if googletrans is None:
		core.MY_PRINT_FUNC("ERROR: Python library 'googletrans' not installed, translation will be very limited!!")
		core.MY_PRINT_FUNC("Please install this library with 'pip install googletrans' in Windows Command Prompt")
		jp_to_en_google = None
	else:
		# everything is fine, just set up the normal way
		jp_to_en_google = googletrans.Translator()
	
	# if JP model name is empty, give it something. same for comment
	if pmx[0][1] == "":
		pmx[0][1] = "model"
	if pmx[0][3] == "":
		pmx[0][3] = "comment"
	
	translate_maps = []
	
	
	# repeat the following for each category of visible names:
	# materials=4, bones=5, morphs=6, dispframe=7
	for cat_id in range(4, 8):
		category = pmx[cat_id]
		# for each entry:
		for d, item in enumerate(category):
			if cat_id == 7 and item[2]: continue  # skip "special" display frames
			# jp=0,en=1
			# strip away newline and return just in case, i saw a few examples where they showed up
			item[0] = item[0].replace('\r','').replace('\n','')
			item[1] = item[1].replace('\r','').replace('\n','')
			# try to apply "easy" translate methods
			newname, source = easy_translate(item[0], item[1], specificdict_dict[cat_id])
			# build the "trans_entry" item from this result, regardless of pass/fail
			newentry = translate_entry(item[0], item[1], cat_id, d, newname, source)
			# store it
			translate_maps.append(newentry)
			
	# model name is special cuz there's only one & its indexing is different
	# but i'm doing the same stuff
	pmx[0][1] = pmx[0][1].replace('\r', '').replace('\n', '')
	pmx[0][2] = pmx[0][2].replace('\r', '').replace('\n', '')
	# try to apply "easy" translate methods
	newname, source = easy_translate(pmx[0][1], pmx[0][2], None)
	# build the "trans_entry" item from this result, regardless of pass/fail
	newentry = translate_entry(pmx[0][1], pmx[0][2], 0, 2, newname, source)
	# store it
	translate_maps.append(newentry)
	
	if TRANSLATE_MODEL_COMMENT:
		# here, attempt to match model comment with type0 (already good) or type1 (copy JP)
		newcomment, newcommentsource = easy_translate(pmx[0][3], pmx[0][4], None)
	else:
		newcomment = pmx[0][4]
		newcommentsource = 0  # 0 means kept good aka nochange
		
	# now I have all the translateable items (except for model comment) collected in one list
	# partition the list into done and notdone
	translate_maps, translate_notdone = my_list_partition(translate_maps, lambda x: x.trans_type != -1)
	########
	# actually do local translate
	local_results = translation_tools.local_translate([item.jp_old for item in translate_notdone])
	# determine if each item passed or not, update the en_new and trans_type fields
	for item, result in zip(translate_notdone, local_results):
		if not translation_tools.needs_translate(result):
			item.en_new = result
			item.trans_type = 3
	# grab the newly-done items and move them to the done list
	translate_done2, translate_notdone = my_list_partition(translate_notdone, lambda x: x.trans_type != -1)
	translate_maps.extend(translate_done2)
	########
	if not PREFER_EXISTING_ENGLISH_NAME:
		# if i chose to anti-prefer the existing EN name, then it is still preferred over google and should be checked here
		for item in translate_notdone:
			# first, if en name is already good (not blank and not JP), just keep it
			if item.en_old and not item.en_old.isspace() and not translation_tools.needs_translate(item.en_old):
				item.en_new = item.en_old
				item.trans_type = 0
		# transfer the newly-done things over to the translate_maps list
		translate_done2, translate_notdone = my_list_partition(translate_notdone, lambda x: x.trans_type != -1)
		translate_maps.extend(translate_done2)
	
	########
	# actually do google translate
	num_items = len(translate_notdone) + (newcommentsource != 0)
	if num_items:
		core.MY_PRINT_FUNC("Identified %d items that need Internet translation..." % num_items)
		try:
			google_results = google_translate([item.jp_old for item in translate_notdone])
			# determine if each item passed or not, update the en_new and trans_type fields
			for item, result in zip(translate_notdone, google_results):
				# save the result regardless of pass/fail, it's the best I've got
				item.en_new = result
				if not translation_tools.needs_translate(result):
					item.en_new = result
					item.trans_type = 4
			# grab the newly-done items and move them to the done list
			# translate_done2, translate_notdone = separate_notdone(translate_notdone)
			translate_maps.extend(translate_notdone)
			if TRANSLATE_MODEL_COMMENT and newcommentsource == -1:  # -1 = pending, 0 = did nothing, 4 = did something
				# if i am going to translate the comment, but was unable to do it earlier, then do it now
				core.MY_PRINT_FUNC("Now translating model comment")
				comment_clean = pmx[0][3].replace("\r", "")  # delete these \r chars, google doesnt want them
				comment_clean = comment_clean.strip()
				########
				# actually do google translate
				if check_translate_budget(1):
					newcomment = _single_google_translate(comment_clean)
					newcomment = newcomment.replace('\n', '\r\n')  # put back the /r/n, MMD needs them
					newcommentsource = 4
				else:
					newcomment = pmx[0][4]
					newcommentsource = 0
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("Internet translate unexpectedly failed, attempting to recover...")
	
	###########################################
	# done translating!!!!!
	###########################################
	
	# now, determine if i actually changed anything at all before bothering to try applying stuff
	type_fail, temp = 		my_list_partition(translate_maps, lambda x: x.trans_type == -1)
	type_good, temp = 		my_list_partition(temp, lambda x: x.trans_type == 0)
	type_copy, temp = 		my_list_partition(temp, lambda x: x.trans_type == 1)
	type_exact, temp = 		my_list_partition(temp, lambda x: x.trans_type == 2)
	type_local, temp = 		my_list_partition(temp, lambda x: x.trans_type == 3)
	type_google = 			temp
	total_changed = int(newcommentsource != 0) + len(type_copy) + len(type_exact) + len(type_local) + len(type_google)
	total_fields = len(translate_maps)
	if total_changed == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	if type_fail:
		# TODO: test this & think about this more
		core.MY_PRINT_FUNC("Warning: %d items were unable to be translated by Google, try running translation again" % len(type_fail))
		
	###########################################
	# next, apply!
	# comment
	if TRANSLATE_MODEL_COMMENT and newcommentsource != 0:
		pmx[0][4] = newcomment
	# everything else: iterate over all entries, write when anything has type != 0
	# even write when type=-1=fail (if enabled), because it's the best I've got
	for item in translate_maps:
		if item.trans_type > 0 or (ACCEPT_INCOMPLETE_RESULT and item.trans_type == -1):
			if item.cat_id == 0:  # this is header-type
				pmx[item.cat_id][item.idx] = item.en_new
			else:  # this is anything else
				pmx[item.cat_id][item.idx][1] = item.en_new
	
	###########################################
	# next, print info!
	core.MY_PRINT_FUNC("Translated {} / {} = {:.1%} english fields in the model".format(
		total_changed, total_fields, total_changed / total_fields))
	if moreinfo:
		# give full breakdown of each source
		core.MY_PRINT_FUNC("Total fields={}, nochange={}, copy={}, exactmatch={}, piecewise={}, Google={}, fail={}".format(
			total_fields, len(type_good), len(type_copy), len(type_exact), len(type_local), len(type_google), len(type_fail)))
		#########
		# now print the table of before/after/etc
		# hide good/copyJP/exactmatch cuz those are uninteresting and guaranteed to be safe
		maps_printme = [item for item in translate_maps if item.trans_type > 2 or (ACCEPT_INCOMPLETE_RESULT and item.trans_type == -1)]
		if maps_printme:
			width = []
			# columns: category, idx, trans_type, en_old, en_new, jp_old = 6 types
			# bone  15  google || EN: 'asdf' --> 'foobar' || JP: 'fffFFFff'
			# find max width of each column: this doesn't properly handle JP chars but w/e good enough for now
			width.append(max([len(category_dict[vv.cat_id]) for vv in maps_printme]))
			width.append(max([len(str(vv.idx)) for vv in maps_printme]))
			width.append(max([len(type_dict[vv.trans_type]) for vv in maps_printme]))
			width.append(2 + max([len(vv.en_old) for vv in maps_printme]))
			width.append(2 + max([len(vv.en_new) for vv in maps_printme]))
			# width.append(2 + max([len(vv.jp_old) for vv in maps_printme]))
			
			# SORT THE LIST!
			maps_printme.sort(key=lambda x: x.idx)
			maps_printme.sort(key=lambda x: x.cat_id)
			
			# now pretty-print the list of translations:
			for tmap in maps_printme:
				# print a line for each item
				core.MY_PRINT_FUNC("{:{widtha}} {:>{widthb}} {:{widthc}} || EN: {:{widthd}} --> {:{widthe}} || JP: {}".format(
					category_dict[tmap.cat_id],
					tmap.idx,
					type_dict[tmap.trans_type],
					"'" + tmap.en_old + "'",
					"'" + tmap.en_new + "'",
					"'" + tmap.jp_old + "'",
					widtha=width[0],
					widthb=width[1],
					widthc=width[2],
					widthd=width[3],
					widthe=width[4]))
	
	###########################################
	# next, return!
	return pmx, True
	
	
def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_translate.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = translate_to_english(pmx, moreinfo=True)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/10/2020 - v4.08")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
