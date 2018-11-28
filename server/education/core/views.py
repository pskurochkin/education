import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Region, University, Specialty, Subject, Variant
import numpy as np
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import random
import math


class TrieNode:
    def __init__(self, char):
        self.node_key = char
        self.node = {self.node_key: []}
        self.is_finish_node = False

    def key(self):
        return self.node_key

    def values(self):
        return self.node[self.node_key]

    def append(self, node):
        self.node[self.node_key].append(node)


class Trie:
    def __init__(self):
        self.root = TrieNode('')

    def add(self, word):
        parent_node = self.root
        for char in word:
            find_char_in_nodes = False
            for node in parent_node.values():
                if char == node.key():
                    parent_node = node
                    find_char_in_nodes = True
                    break
            if not find_char_in_nodes:
                new_node = TrieNode(char)
                parent_node.append(new_node)
                parent_node = new_node
        parent_node.is_finish_node = True

    def suggest(self, string):
        def bfs(node):
            arr = []
            if node.is_finish_node:
                arr.append(node.key())
            if node.values() != []:
                values = node.values()
                for v in values:
                    returned_arr = bfs(v)
                    for i in range(len(returned_arr)):
                        arr.append(node.key() + returned_arr[i])
            return arr

        parent_node = self.root
        for char in string:
            find_char_in_nodes = False
            for node in parent_node.values():
                if char == node.key():
                    parent_node = node
                    find_char_in_nodes = True
                    break
            if not find_char_in_nodes:
                return
        prefix = string[:len(string) - 1]
        suggest = bfs(parent_node)
        for i in range(len(suggest)):
            suggest[i] = prefix + suggest[i]
        return suggest


regions = Region.objects.values_list('name', flat=True)
prefix_tree = Trie()
for region in regions:
    prefix_tree.add(region)

ratings = []
for variant in Variant.objects.filter(university__place__isnull=False):
    ratings.append([variant.rating, variant.budget_passing_score])
ratings = np.array(ratings)
plt.scatter(ratings[:, 0], ratings[:, 1], alpha=.75)
plt.savefig('./core/static/fig0.png')
plt.close()


def hello(request):
    return render(request, 'index.html', {'subjects': Subject.objects.all()})


def get_suggest(request):
    if request.GET['query'] == '':
        return JsonResponse({'results': []})
    suggests = prefix_tree.suggest(request.GET['query'])
    if not suggests:
        return JsonResponse({'results': []})
    suggests = [{'name': x} for x in suggests]
    return JsonResponse({'results': suggests})


@csrf_exempt
def get_variants(request):
    data = json.loads(request.body)
    regions = Region.objects.filter(name__in=data['regions_name'])
    universities = University.objects.filter(region__in=regions)

    exams = {}
    for subject in data['subjects']:
        if subject['value'] == '':
            continue
        if int(subject['value']) > 30:
            exams.update({Subject.objects.get(id=subject['id']).name: int(subject['value'])})
    score = sum(exams.values())

    variants = []
    for variant in Variant.objects.filter(university__in=universities):
        includes = True
        for subject in variant.subjects.all():
            if not (subject.name in list(exams.keys())):
                includes = False
        if includes and variant.university.place != None:
            variants.append(variant)

    variants_filtered = []
    X = []
    X_log = []
    for variant in variants:
        passing_score = variant.budget_passing_score
        if int(passing_score) <= score + 10:
            variants_filtered.append(variant)
            X_log.append([variant.rating, variant.budget_passing_score])
            place = variant.university.place * variant.specialty.place
            X.append([place, variant.budget_passing_score])

    X = np.array(X)
    plt.scatter(X[:, 0], X[:, 1], alpha=.75)
    plt.savefig('./core/static/fig1.png')
    plt.close()

    X_log = np.array(X_log)

    mean_ = X_log.mean(axis=0)
    std_ = X_log.std(axis=0)
    X_log = (X_log - mean_) / std_

    _sum = np.sum(X_log, axis=0)
    centroid = [_sum[0] / X_log.shape[0], _sum[1] / X_log.shape[0]]
    X_log -= centroid

    plt.scatter(X_log[:, 0], X_log[:, 1], alpha=.75)

    pca = PCA()
    pca.fit(X_log)
    print('Proportion of variance explained by each component:\n' + \
          '1st component - %.3f,\n2nd component - %.3f\n' %
          tuple(pca.explained_variance_ratio_))
    print('Directions of principal components:\n' + \
          '1st component:', pca.components_[0],
          '\n2nd component:', pca.components_[1])

    for l, v in zip(pca.explained_variance_ratio_, pca.components_):
        d = 5 * np.sqrt(l) * v
        plt.plot([0, d[0]], [0, d[1]], 'black')

    plt.axis('equal')
    plt.savefig('./core/static/fig2.png')
    plt.close()

    X_reduced = pca.fit_transform(X_log)
    X_reduced[:, 1] = 0
    if pca.components_[0][1] < 0:
        X_reduced = -X_reduced
    X_new = pca.inverse_transform(X_reduced)

    X_reduced_min = np.min(X_reduced, axis=0)[0]
    X_reduced += [-X_reduced_min + 1, 0]
    coif = X_reduced[:, 0]

    index = 0
    my_rating = []
    for variant in variants_filtered:
        passing_score = variant.budget_passing_score
        my_place = 1
        for _ in range(int(variant.budget_plan * coif[index])):
            random_score = random.randint(int(passing_score * .9), int(passing_score * 1.2))
            if random_score > score:
                my_place += 1
        my_rating.append(round(math.exp(-my_place * 1.25 / passing_score), 3))
        index += 1

    plt.scatter(X_log[:, 0], X_log[:, 1], alpha=.75)
    plt.plot(X_new[:, 0], X_new[:, 1], 'or', alpha=0.3)
    plt.axis('equal')
    plt.savefig('./core/static/fig3.png')
    plt.close()

    var_ratings = []
    index = 0
    for variant in variants_filtered:
        var_ratings.append([variant.specialty.name,
                            variant.university.name,
                            variant.budget_passing_score,
                            variant.budget_plan,
                            my_rating[index],
                            100-X_reduced[index, 0]])
        index += 1
    var_ratings = np.array(var_ratings)
    var_ratings = var_ratings[var_ratings[:, 5].argsort()]

    var = []
    for i in range(len(var_ratings)):
        var.append({'specialty_name': var_ratings[i, 0],
                    'university_name': var_ratings[i, 1],
                    'passing_score': var_ratings[i, 2],
                    'plan': var_ratings[i, 3],
                    'score': var_ratings[i, 4]})
    return JsonResponse(var, safe=False)


def show_plots(request):
    return render(request, 'plots.html')
