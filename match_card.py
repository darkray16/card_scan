import os
import sqlite3
from cv_utils import ccoeff_normed, img_from_buffer


def load_sets(base_dir, set_names):
	cards = []
	for dir, subdirs, fnames in os.walk(base_dir):
		set = os.path.split(dir)[1]
		if set in set_names:
			for fname in fnames:
				path = os.path.join(dir, fname)

				img = cv.LoadImage(path,0)
				if cv.GetSize(img) != (223, 310):
					tmp = cv.CreateImage((223, 310), 8, 1)
					cv.Resize(img,tmp)
					img = tmp
				angle_map = gradient(img)[1]
				hist = angle_hist(angle_map)

				cards.append((
					fname.replace('.full.jpg',''),
					set,
					angle_map,
					hist
				))
	return cards

def match_db_cards(known):
	connection = sqlite3.connect("inventory.sqlite3")
	try:
		cursor = connection.cursor()
		cursor.execute("select rowid, scan_png from inv_cards where recognition_status is 'scanned'")
		row = cursor.fetchone()
		while row is not None:
			try:
				id, buf = row
				img = img_from_buffer(buf)
				card, set = match_card(img, known)
				card = unicode(card.decode('UTF-8'))
				cv.ShowImage('debug', img)
				print "set row %s to %s/%s" % (id, set, card)
				update_c = connection.cursor()
				update_c.execute("update inv_cards set name=?, set_name=?, recognition_status=? where rowid=?", [card, set, 'candidate_match', id])
				connection.commit()
			except KeyboardInterrupt as e:
				raise e
			except Exception as e:
				print "failure on row %s" % row[0]
				print e
			finally:
				row = cursor.fetchone()
	finally:
		connection.close()

#*********************
#card matching section
def gradient(img):
	cols, rows = cv.GetSize(img)

	x_drv = cv.CreateMat(rows,cols,cv.CV_32FC1)
	y_drv = cv.CreateMat(rows,cols,cv.CV_32FC1)
	mag = cv.CreateMat(rows,cols,cv.CV_32FC1)
	ang = cv.CreateMat(rows,cols,cv.CV_32FC1)

	cv.Sobel(img, x_drv, 1, 0)
	cv.Sobel(img, y_drv, 0, 1)
	cv.CartToPolar(x_drv,y_drv,mag,ang)
	return (mag,ang)

def angle_hist(mat):
	h = cv.CreateHist([9], cv.CV_HIST_ARRAY, [(0.001,math.pi*2)], True)
	cv.CalcHist([cv.GetImage(mat)], h)
	#cv.NormalizeHist(h,1.0)
	return h

def score(card, known, method):
	r = cv.CreateMat(1, 1, cv.CV_32FC1)
	cv.MatchTemplate(card, known, r, method)
	return r[0,0]

def match_card(card, known_set):
	mag, grad = gradient(card)
	#h = angle_hist(grad)
	#limited_set = sorted([(cv.CompareHist(h, hist, cv.CV_COMP_CORREL), name, set, g) for name,set,g,hist in known_set], reverse=True)[0:1000]
	#h_score, name, set, img = max(limited_set,
	#	key = lambda (h_score, name, set, known): score(grad, known, cv.CV_TM_CCOEFF)
	#)
	name, set, g, h = max(known_set,
		key = lambda (n, s, g, h): ccoeff_normed(g,grad)
	)
	return (name, set)

LIKELY_SETS = [
	'DKA', 'ISD',
	'NPH', 'MBS', 'SOM',
	'ROE', 'WWK', 'ZEN',
	'ARB', 'CON', 'ALA',
	'EVE', 'SHM', 'MOR', 'LRW',
	'M12', 'M11', 'M10', '10E',
	'HOP',
]
