import os
from os.path import join
import numpy as np
from scipy import sparse
from scipy.sparse import linalg
import math
import time
import operator
import random

np.set_printoptions(precision = 5)
np.seterr(divide='ignore', invalid='ignore')

def rmse_spearman(matrix, matrix_test, path):
	"""
	Calculates the RMSE error and Spearman correlation

	Parameters:
	matrix: this matrix contains detected values
	matrix_test: this matrix contains original values
	path: this is the path to the test file containing testing instances
	"""
	# start = time.time()
	total = 0.0
	test_file = open(path, 'r')
	for i, line in enumerate(test_file):
		values = line.split(',')
		r, c = int(values[0])-1, int(values[1])-1
		total+= math.pow((matrix_test[r, c] - (matrix[r, c])), 2)
	i+=1
	rho = 1 - (6*total)/(i*(math.pow(i,2) - 1))
	# print('\nRMSE and Spearman Correlation calculated in ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	test_file.close()
	rmse, spear = math.sqrt(total)/i, rho
	print('\nRMSE Error : ' + str(rmse) + '\t Spearman Correlation : ' + str(spear*100) + '%\n')

def svd(sparse_matrix, no_eigen_values, energy = 1):
	"""
	Perform SVD Decomposition on the input sparse_matrix
	Pass the copy of the sparse matrix to keep the original matrix unchanged

	Parameters:
	sparse_matrix : input sparse_matrix
	no_eigen_values: number of largest eigen values desired
	energy: retain energy% of largest eigen values

	Returns : The dot product of U S and Vt matrix
	"""

	print('\n' + '-'*10 + ' SVD with ' + str(energy*100) + '% energy ' + '-'*10)
	start = time.time()
	u,s,vt = svd_retain_energy(sparse_matrix, no_eigen_values, energy)
	svd_matrix = np.dot(np.dot(u,np.diag(s)), vt)
	print('\nSVD Decomposition with ' + str(energy*100) + '% energy took ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	return svd_matrix

def svd_retain_energy(sparse_matrix, no_eigen_values, energy = 1):
	u,s,vt = linalg.svds(sparse_matrix, k = no_eigen_values)
	s_squared_sum = np.square(s).sum()		# sum of square of all eigen values (diagnol elements in s)
	for i in range(s.shape[0]):
		if np.square(s[i:]).sum()<(energy*s_squared_sum):
			break
	i-=1
	return np.delete(u, np.s_[:i], 1), s[i:], np.delete(vt, np.s_[:i], 0)


def intersection_sparse(sparse_matrix, rows_list_original, cols_list_original):
	"""
	Parameters:
	sparse_matrix: the original matrix in sparse form
	rows_prob: a list of the indices of the selected rows for R matrix
	col_list: a list of the indices of the selected columns for C matrix

	Returns:
	sparse matrix W such that W consists of elements sparse_matrix[i,j] for all i, j in rows_list, cols_list respectively
	"""

	rows_list, cols_list = [], []			# modified row and column list to create intersection matrix
	no_cols = len(rows_list_original)
	for item in rows_list_original:
		rows_list.extend([item] * no_cols)
	cols_list.extend(cols_list_original * no_cols)
	data_list = [sparse_matrix[r,cols_list[i]] for i, r in enumerate(rows_list)]
	rows_list, cols_list, zero_indices = [], [], []
	for i in range(no_cols):
		rows_list.extend([i] * no_cols)
	cols_list.extend(list(range(no_cols)) * no_cols)
	# delete zero values from data_list and corresponding rows and cols from rows_list and cols_list
	for i, item in enumerate(data_list):
		if item == 0:
			zero_indices.append(i)
	for index in sorted(zero_indices, reverse = True):
		del data_list[index]
		del rows_list[index]
		del cols_list[index]
	row = np.array(rows_list, dtype = np.float32)
	col = np.array(cols_list, dtype = np.float32)
	data = np.array(data_list, dtype = np.float32)
	# form sparse intersection matrix
	W = sparse.coo_matrix((data, (row, col)), shape=(no_cols, no_cols)).tocsr()
	return W

def cur(sparse_matrix, no_cols, no_eigen_values, energy = 1):
	"""
	Perform CUR Decomposition on the input sparse_matrix

	Parameters:
	sparse_matrix : input sparse_matrix
	no_cols: number of columns and rows to select
	no_eigen_values: number of largest eigen values desired while performing SVD on W matrix
	energy: retain energy% of largest eigen values

	Returns : The dot product of C U and R matrix
	"""

	print('\n' + '-'*10 + ' CUR with ' + str(energy*100) + '% energy ' + '-'*10)
	start = time.time()
	def select_columns(sparse_matrix_csc, select_col = True):
		sparse_copy = sparse_matrix_csc.copy()
		sparse_matrix_csc = sparse_matrix_csc.power(2)
		total_sum = sparse_matrix_csc.sum()
		col_prob = []	# col_prob contains (indices of column, probabilty of that column)
		for c in range(sparse_matrix_csc.shape[1]):
			col_prob.append((c,sparse_matrix_csc.getcol(c).sum()/total_sum))
		# discard columns with zero frobenius norm
		zero_indices = []
		for i, item in enumerate(col_prob):
			if item[1] == 0:
				zero_indices.append(i)
		for index in sorted(zero_indices, reverse = True):
			del col_prob[index]
		# randomly sample no_cols from the matrix
		col_prob = random.sample(col_prob, no_cols)
		col_prob.sort(key = operator.itemgetter(0))
		C = sparse.lil_matrix((sparse_copy.shape[0], no_cols))
		for i in range(no_cols):
			C[:,i] = sparse_copy.getcol(col_prob[i][0])/math.sqrt(no_cols*col_prob[i][1])
			# C[:,i] = sparse_copy[:, col_prob[i][0]]/math.sqrt(no_cols*col_prob[i][1])
		if select_col:
			return C.tocsc(), col_prob
		else:
			return C.transpose().tocsc(), col_prob
	
	# print(sparse_matrix.todense())
	# select columns to fill C matrix
	C, col_prob = select_columns(sparse_matrix.tocsc())
	# select rows to fill R matrix
	R, row_prob = select_columns(sparse_matrix.transpose().tocsc(), select_col=False)
	# create W matrix (intersection of C and R)
	W = intersection_sparse(sparse_matrix, sorted([x[0] for x in row_prob]), sorted([x[0] for x in col_prob]))
	print('\nBuilding C, R, W matrix took ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	# perform svd on W
	# x,z,yt = linalg.svds(W, k = no_eigen_values)
	x,z,yt = svd_retain_energy(W, no_eigen_values, energy)
	# form U matrix
	U = np.dot(np.dot(np.transpose(yt), np.linalg.matrix_power(np.diag(np.reciprocal(z)),2)), np.transpose(x))
	# U = np.dot(np.dot(np.transpose(yt), np.linalg.matrix_power(np.reciprocal(z),2)), np.transpose(x))
	cur_matrix = np.dot(np.dot(C.todense(), U), R.todense())
	print('\nCUR Decomposition took ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	return cur_matrix

def collaborative(sparse_matrix, sparse_matrix_original, sparse_matrix_test_original, k,  baseline = False):
	"""
	Perform collaborative filtering on sparse_matrix

	Parameters:
	sparse_matrix: the input normalized sparse matrix
	sparse_matrix_original: original sparse matrix
	sparse_matrix_test_original: sparse test matrix with just testing instances
	k: size of neighbourhood
	baseline: determines whether to do normal collaborative or collaborative with baseline approach

	"""
	if not baseline:
		print('\n' + '-'*10 + ' Collaborative Filtering ' + '-'*10)
	else:
		print('\n' + '-'*10 + ' Collaborative Filtering with Baseline Approach' + '-'*10)
	start = time.time()
	# collaborative_matrix = sparse.dok_matrix(sparse_matrix_original)
	collaborative_matrix = sparse_matrix_original.toarray()
	# store rows and norm(row)
	row_norm = []
	for r in range(sparse_matrix.shape[0]):
		row_norm.append(linalg.norm(sparse_matrix.getrow(r)))
	row_norm = np.array(row_norm).reshape((sparse_matrix.shape[0], 1))

	# store product of norm every 2 rows in users in row_norm_products
	row_norm_products = np.dot(row_norm, np.transpose(row_norm))

	# store dot product of every 2 rows in dot_products
	dot_products = sparse_matrix.dot(sparse_matrix.transpose()).toarray()

	# get indices of upper triangular matrix
	iu1 = np.triu_indices(dot_products.shape[0], 1)
	rowu_indices, colu_indices = iu1
	# store similarities for each user-user tuple
	similarity = np.diag(np.array([-2 for x in range(sparse_matrix.shape[0])], dtype = np.float32))
	similarity[rowu_indices, colu_indices] = dot_products[rowu_indices,colu_indices]/row_norm_products[rowu_indices, colu_indices]
	similarity[np.isnan(similarity)] = 0.0
	# copy upper triangular values to lower triangle
	similarity.T[rowu_indices, colu_indices] = similarity[rowu_indices, colu_indices]
	
	# store indices of closest k users for every user
	neighbourhood = np.zeros((sparse_matrix.shape[0], k), dtype = np.int)
	for i in range(sparse_matrix.shape[0]):
		neighbourhood[i] = similarity[i,:].argsort()[-k:][::-1]
	t1 = time.time()
	print('\nCalculated similarities and founded neighbourhoods in ' + '{0:.2f}'.format(t1 - start) + ' secs.')

	# store similarity of user u with its k neighbours
	row_indices, col_indices = np.indices(neighbourhood.shape)
	similarity_user_neighbour = np.zeros(neighbourhood.shape, dtype = np.float32)
	similarity_user_neighbour[row_indices, col_indices] = similarity[row_indices,neighbourhood[row_indices,col_indices]]

	# Below commented lines improve the performance BUT...
	# Uncomment below lines only if you have the RAM it takes to store sparse_matrix.shape[0]*sparse_matrix.shape[1]*k > 10GB worth floats in memory!

	# t2 = time.time()
	# # store user_x-user_y similarity * rating_user_y for every user x (y are the neighbours of x)
	# similarity_rating_product = np.zeros((collaborative_matrix.shape[0], collaborative_matrix.shape[1], k), dtype = np.float32)
	# row_indices, col_indices = sparse_matrix_test_original.nonzero()
	# neighbour_indices = np.indices(similarity_rating_product.shape)[2]
	# similarity_rating_product[row_indices, col_indices, neighbour_indices] = similarity_user_neighbour[row_indices, neighbour_indices] * collaborative_matrix[neighbourhood[row_indices,neighbour_indices], col_indices]

	# t3 = time.time()
	# print('\nCalulated similarity_rating_product in ' + '{0:.2f}'.format(t3 - t2) + ' secs.')

	# # get indices of non-zero elements from test matrix
	# row_test_indices, col_test_indices = sparse_matrix_test_original.nonzero()
	# # calculate rating of user r for movie c, where (r,c) are testing instances
	# collaborative_matrix[row_test_indices, col_test_indices] = similarity_rating_product[row_test_indices, col_test_indices].sum() / similarity_user_neighbour[row_test_indices].sum()
	# # print(collaborative_matrix)

	# t4 = time.time()
	# print('\nCalulated collaborative_matrix in ' + '{0:.2f}'.format(t4 - t3) + ' secs.')

	row_test_indices, col_test_indices = sparse_matrix_test_original.nonzero()
	
	if not baseline:
		for i, (r, c) in enumerate(zip(row_test_indices, col_test_indices)):
			if((i+1)%40000) == 0:
				print('Predicted ' + str(i+1) + ' ratings.')
			elif(i+1 == len(row_test_indices)):
				print('Predicted all ' + str(i+1) + ' ratings.')
			collaborative_matrix[r, c] = np.dot(similarity_user_neighbour[r], np.array([collaborative_matrix[j,c] for j in neighbourhood[r]]))/(similarity_user_neighbour[r].sum())

		print('\nCollaborative filtering took ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	else:
		# find mean of whole original sparse matrix
		t1 = time.time()
		mean = sparse_matrix_original.sum()/(sparse_matrix_original!=0).sum()
		# find mean rating for every user
		user_mean = (np.squeeze(np.array(sparse_matrix_original.sum(axis = 1)/(sparse_matrix_original!=0).sum(axis = 1)))).tolist()
		# find mean rating of every movie
		movie_mean = (np.squeeze(np.array(sparse_matrix_original.sum(axis = 0)/(sparse_matrix_original!=0).sum(axis = 0)))).tolist()
		
		# row_indices, col_indices = sparse_matrix_original.nonzero()
		# data = np.array([user_mean[r] + movie_mean[c] - mean for (r,c) in zip(row_indices, col_indices)])
		# baseline_matrix = sparse.coo_matrix((data, (row_indices,col_indices)),shape = sparse_matrix_original.shape).toarray()

		for i, (r, c) in enumerate(zip(row_test_indices, col_test_indices)):
			if((i+1)%40000) == 0:
				print('Predicted ' + str(i+1) + ' ratings.')
			elif(i+1 == len(row_test_indices)):
				print('Predicted all ' + str(i+1) + ' ratings.')
			# collaborative_matrix[r, c] = baseline_matrix[r,c] + np.dot(similarity_user_neighbour[r], np.array([collaborative_matrix[j,c]-baseline_matrix[j,c] for j in neighbourhood[r]]))/(similarity_user_neighbour[r].sum())
			collaborative_matrix[r, c] = user_mean[r] + np.dot(similarity_user_neighbour[r], np.array([collaborative_matrix[j,c]-user_mean[j] for j in neighbourhood[r]]))/(similarity_user_neighbour[r].sum())
		print('\nCollaborative filtering with baseline approach took ' + '{0:.2f}'.format(time.time() - start) + ' secs.')
	
	collaborative_matrix[np.isnan(collaborative_matrix)] = 0.0
	return collaborative_matrix

def main():

	# path to datasets and test files
	dataset_dir = join(os.getcwd(), 'Datasets', 'Movie Lens Movie Recommendation Dataset', 'ml-1m')
	test_file_path = join(dataset_dir, 'ratings_test.txt')
	test_file_path_collaborative = join(dataset_dir, 'ratings_test.txt')
	
	# load sparse matrix
	# train matrix with 750156 ratings
	sparse_matrix_train_normalized = sparse.load_npz('ratings_train_normalized.npz')
	sparse_matrix_train_original = sparse.load_npz('ratings_train_original.npz')

	# test matrix with 250053 ratings
	sparse_matrix_test_normalized = sparse.load_npz('ratings_test_normalized.npz')
	sparse_matrix_test_original = sparse.load_npz('ratings_test_original.npz')

	# test matrix with 200 ratings
	sparse_matrix_test_200_original = sparse.load_npz('ratings_test_200_original.npz').todok()
	sparse_matrix_test_200_normalized = sparse.load_npz('ratings_test_200_normalized.npz').todok()

	################################################################################################################
	# Testing with small matrix
	# test_file_path = 'temp_test.txt'
	# # train matrix
	# sparse_matrix_train_normalized = sparse.load_npz('temp_normalized.npz')
	# sparse_matrix_train_original = sparse.load_npz('temp_original.npz')

	# # test matrix
	# sparse_matrix_test_200_original = sparse.load_npz('temp_test_original.npz').todok()
	# print(sparse_matrix_test_200_original)

	# # collaborative_matrix = collaborative(sparse_matrix_train_normalized, sparse_matrix_train_original, sparse_matrix_test_200_original, 2)
	# # rmse_spearman(collaborative_matrix, sparse_matrix_test_200_original, test_file_path)

	# # collaborative with baseline approach
	# collaborative_matrix_baseline = collaborative(sparse_matrix_train_normalized, sparse_matrix_train_original, sparse_matrix_test_200_original, 2, baseline = True)
	# rmse_spearman(collaborative_matrix_baseline, sparse_matrix_test_200_original, test_file_path)

	################################################################################################################

	# perform collaborative filtering
	collaborative_matrix = collaborative(sparse_matrix_train_normalized, sparse_matrix_train_original, sparse_matrix_test_original, 150)
	rmse_spearman(collaborative_matrix, sparse_matrix_test_original, test_file_path_collaborative)

	# collaborative with baseline approach
	collaborative_matrix_baseline = collaborative(sparse_matrix_train_normalized, sparse_matrix_train_original, sparse_matrix_test_original, 150, baseline = True)
	rmse_spearman(collaborative_matrix_baseline, sparse_matrix_test_original, test_file_path_collaborative)

	# perform svd and cur and calculate errors
	concepts = 40	# number of concepts/eigen values to consider while performing SVD decomposition
	svd_matrix = svd(sparse_matrix_train_normalized, concepts, energy = 1)
	rmse_spearman(svd_matrix, sparse_matrix_test_normalized.todok(), test_file_path)
	svd_matrix = svd(sparse_matrix_train_normalized, concepts, energy = 0.9)
	rmse_spearman(svd_matrix, sparse_matrix_test_normalized.todok(), test_file_path)
	cur_matrix = cur(sparse_matrix_train_normalized, 4*concepts, concepts, energy = 1)
	rmse_spearman(cur_matrix, sparse_matrix_test_normalized.todok(), test_file_path)
	cur_matrix = cur(sparse_matrix_train_normalized, 4*concepts, concepts, energy = 0.9)
	rmse_spearman(cur_matrix, sparse_matrix_test_normalized.todok(), test_file_path)

if __name__ == '__main__':
	main()