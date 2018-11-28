from django.core.management.base import BaseCommand, CommandError
from core.models import Region, University, Specialty, Subject, Variant
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import re
import math


# Метод для получения всех регионов
def get_regions():
    url = 'https://education.yandex.ru/universities/'
    text = requests.get(url).text

    p = re.compile(r'\"id\":(\d{3}),\"title\":\"([\w ()-—]+)\",\"geoId\"')
    pairs = p.findall(text)

    regions = {}
    for key, value in pairs:
        key = int(key)
        regions.update({key: value})

    return regions


# Метод для получения id всех университетов определенного региона
def get_universities_id(region_id, specialties_id):
    url = 'https://education.yandex.ru/universities/graphql'

    payload = {
        "query": "query SearchQuery($year: Int!, $subjectsStats: [SubjectScoreInput!]!, $possibleEducationTypes: [EDUCATION_TYPE!]!, $specialtyIds: [Int!], $regionsIds: [Int!], $requireMilitaryReserve: Boolean, $requireMilitaryContract: Boolean, $requireDormitory: Boolean) {\n  search(input: {year: $year, subjectsStats: $subjectsStats, possibleEducationTypes: $possibleEducationTypes, specialtyIds: $specialtyIds, regionsIds: $regionsIds, requireMilitaryReserve: $requireMilitaryReserve, requireMilitaryContract: $requireMilitaryContract, requireDormitory: $requireDormitory}) {\n    id\n    title\n    abbreviation\n    city\n    showCity\n    parent {\n      id\n      title\n      abbreviation\n      __typename\n    }\n    admissions {\n      id\n      srcYear\n      subjectIds\n      budgetMinPointsSum\n      paidMinPointsSum\n      tuition\n      creativeCompetitions\n      faculties {\n        id\n        title\n        abbreviation\n        __typename\n      }\n      specialtyIds\n      __typename\n    }\n    __typename\n  }\n}\n",
        "variables": {"year": "2017",
                      "subjectsStats": [],
                      "specialtyIds": specialties_id,
                      "possibleEducationTypes": ["APPLIED_BACHELOR", "ACADEMIC_BACHELOR", "SPECIALTY"],
                      "regionsIds": [],
                      "requireMilitaryReserve": False,
                      "requireMilitaryContract": False,
                      "requireDormitory": False},
        "operationName": "SearchQuery"}

    headers = {'Content-Type': 'application/json', }

    payload['variables']['regionsIds'] = [region_id]
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    universities_id = list(map(lambda x: x['id'], response.json()['data']['search']))

    return universities_id


# Метод для получения id всех специальностей
def get_specialties():
    url = 'https://education.yandex.ru/universities/'
    text = requests.get(url).text

    p = re.compile(r'\"id\":(\d{4}),\"code\":\"\d{2}.\d{2}.\d{2}\",\"title\":\"([\w .,()-:]+)\",\"educationTypes\"')
    pairs = p.findall(text)

    specialties = {}
    # specialties_id = []
    for key, value in pairs:
        key = int(key)
        specialties.update({key: value})
        # specialties_id.append(key)

    return specialties


# Метод для получения уровня образования
def get_level(td_list):
    return td_list[0].attrs['title']


# Метод для получения названия специальности
def get_specialty(td_list):
    specialty = td_list[1].text
    pos = specialty.find('«') + 1
    if pos:
        specialty = specialty[pos:specialty.find('»')]
    return specialty


# Метод для получения названия кафедры
def get_department(td_list):
    return td_list[1].text


# Метод для получения массива предметов(экзаменов)
def get_subjects(td_list):
    subjects = []
    for subject in td_list[2].findAll('div', attrs={'class': ['year-stats-subjects-popup__subject']}):
        if subject.attrs['class'] == ['year-stats-subjects-popup__subject']:
            subjects.append(subject.text)
    return subjects


# Метод для получения количества бюджетных мест
def get_budget_plan(td_list):
    budget_plan = None
    if td_list[3].find('div') != None:
        budget_plan = td_list[3].find('div', attrs={'class': ['year-stats-cell-popup__title']}).text
    return budget_plan


# Метод для получения словаря распределения бюджетных мест
def get_budget(td_list):
    budget = None
    if td_list[3].find('div') != None:
        budget = {}
        for row in td_list[3].findAll('div', attrs={'class': ['year-stats-places-popup__row']}):
            budget.update(
                {row.find('span').text: row.find('div', attrs={'class': ['year-stats-places-popup__row-value']}).text})
    return budget


# Метод для получения проходного балла на бюджет
def get_budget_passing_score(td_list):
    budget_passing_score = None
    text = td_list[4].find('div', attrs={'class': ['year-stats-points-popup__points']}).text
    if text != '':
        budget_passing_score = text
    return budget_passing_score


# Метод для получения количества платных мест
def get_paid_plan(td_list):
    paid_plan = None
    if td_list[5].find('div') != None:
        paid_plan = td_list[5].find('div', attrs={'class': ['year-stats-cell-popup__title']}).text
    return paid_plan


# Метод для получения словаря распределения платных мест
def get_paid(td_list):
    paid = None
    if td_list[5].find('div') != None:
        paid = {}
        for row in td_list[5].findAll('div', attrs={'class': ['year-stats-places-popup__row']}):
            paid.update(
                {row.find('span').text: row.find('div', attrs={'class': ['year-stats-places-popup__row-value']}).text})
    return paid


# Метод для получения проходного балла на платное
def get_paid_passing_score(td_list):
    paid_passing_score = None
    text = td_list[6].find('div', attrs={'class': ['year-stats-table-row__right-aligned']}).text
    if text != '':
        paid_passing_score = text
    return paid_passing_score


# Метод для получения стоимости обучения в год
def get_cost(td_list):
    return td_list[7].find('div', attrs={'class': ['year-stats-table-row__right-aligned']}).text.replace(' ',
                                                                                                         '') or None


# Метод для получения рейтингов университетов
def get_universities_rating(university_name):
    url = 'http://vuzoteka.ru/%D0%B2%D1%83%D0%B7%D1%8B/vuzi-form'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    count = 3
    response = requests.post(url, headers=headers, data={'q': university_name[:count]})
    size = response.json()['foundCount']
    stop_counter = 0
    while size == -1 or (size > 1 and stop_counter < 40):
        count += 1
        response = requests.post(url, headers=headers, data={'q': university_name[:count]})
        size_new = response.json()['foundCount']
        if size_new != -1 and size_new == size:
            stop_counter += 1
        size = size_new

    place = None
    if size == 1:
        place = response.json()['data'][0]['place']

    return place


# Метод для получения рейтингов специальностей
def get_specialties_rating():
    url = 'http://vuzoteka.ru/%D0%B2%D1%83%D0%B7%D1%8B/%D1%81%D0%BF%D0%B5%D1%86%D0%B8%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D0%B8'

    soup = BeautifulSoup(requests.get(url).text, 'html.parser')

    specialties_rating = {}

    specialties_raw = soup.findAll('div', attrs={
        'style': ['margin:0px 0 15px 0px; border:1px solid #eee; border-radius:5px;']})
    for specialty in specialties_raw:
        name = specialty.find('a').text
        place = re.match(r'рейтинг\s\(баллы\)\s(\d+)\s\(\d+\)',
                         specialty.find('div', attrs={'class': ['label-part last']}).text).group(1)
        specialties_rating.update({name: int(place)})

    return specialties_rating


# Метод для получения всей информации
def get_info(university_id):
    url = 'https://education.yandex.ru/universities/university/'
    university = requests.get(url + str(university_id))

    soup = BeautifulSoup(university.text, 'html.parser')

    university_name = soup.find('h1', attrs={'class': ['university-title__title']}).text

    table = soup.find('table', attrs={'class': ['year-stats__table']})
    tr_list = table.findAll('tr')

    data = []

    flag_no_department = False
    flag_general = False
    specialty = None
    department = None
    level = None
    subjects = None
    budget_plan = None
    budget = None
    budget_passing_score = None
    paid_plan = None
    paid = None
    paid_passing_score = None
    cost = None

    for tr in tr_list:
        td_list = tr.findAll('td')

        if tr.attrs['class'] == ['year-stats-table-row', 'year-stats-table-row_bold', 'year-stats__data-row']:
            # flag_no_department - нет информации о кафедре
            flag_no_department = td_list[1].text == 'Специальности, факультет для которых уточните в приемной комиссии'

            if not flag_no_department:
                level = get_level(td_list)
                specialty = get_specialty(td_list)

                # flag_general - указаны общие данные
                flag_general = len(td_list) > 2

                if flag_general:
                    subjects = get_subjects(td_list)
                    budget_plan = get_budget_plan(td_list)
                    budget = get_budget(td_list)
                    budget_passing_score = get_budget_passing_score(td_list)
                    paid_plan = get_paid_plan(td_list)
                    paid = get_paid(td_list)
                    paid_passing_score = get_paid_passing_score(td_list)
                    cost = get_cost(td_list)

        elif tr.attrs['class'] == ['year-stats-table-row', 'year-stats__data-row']:
            if flag_no_department:
                level = get_level(td_list)
                specialty = get_specialty(td_list)

            else:
                department = get_department(td_list)

            if not flag_general:
                subjects = get_subjects(td_list)
                budget_plan = get_budget_plan(td_list)
                budget = get_budget(td_list)
                budget_passing_score = get_budget_passing_score(td_list)
                paid_plan = get_paid_plan(td_list)
                paid = get_paid(td_list)
                paid_passing_score = get_paid_passing_score(td_list)
                cost = get_cost(td_list)

            specialty_info = {'level': level,
                              'specialty': specialty,
                              'department': department,
                              'subjects': subjects,
                              'budget_plan': budget_plan,
                              'budget': budget,
                              'budget_passing_score': budget_passing_score,
                              'paid_plan': paid_plan,
                              'paid': paid,
                              'paid_passing_score': paid_passing_score,
                              'cost': cost}

            data.append(specialty_info)

        else:
            # TODO throw exception
            break

    return {university_id: university_name, 'data': data}


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        Region.objects.all().delete()
        University.objects.all().delete()
        Specialty.objects.all().delete()
        Subject.objects.all().delete()
        Variant.objects.all().delete()

        raw_regions_list = [Region(yandex_id=region_id, name=region_name) for region_id, region_name in
                            get_regions().items()]
        regions = Region.objects.bulk_create(raw_regions_list)

        specialties_rating = get_specialties_rating()
        raw_specialties_list = [Specialty(yandex_id=specialty_id,
                                          name=specialty_name,
                                          place=specialties_rating.get(specialty_name, None)) for
                                specialty_id, specialty_name in
                                get_specialties().items()]

        Specialty.objects.bulk_create(raw_specialties_list)

        raw_subjects_list = [Subject(name=subject_name) for subject_name in
                             ['математика', 'русский язык', 'физика',
                              'обществознание', 'биология', 'история',
                              'химия', 'информатика', 'география',
                              'литература', 'иностранный язык']]
        Subject.objects.bulk_create(raw_subjects_list)

        for region in regions:
            for university_id in get_universities_id(region.yandex_id, list(get_specialties().keys())):
                university_info = get_info(university_id)
                variants = university_info['data']
                university = University.objects.create(yandex_id=university_id,
                                                       name=university_info[university_id],
                                                       place=get_universities_rating(university_info[university_id]),
                                                       region=region)
                for variant in variants:
                    subjects = Subject.objects.filter(name__in=variant['subjects'])
                    specialty = Specialty.objects.get(name=variant['specialty'])
                    budget_plan = variant['budget_plan']
                    budget_passing_score = variant['budget_passing_score']
                    paid_plan = variant['paid_plan']
                    paid_passing_score = variant['paid_passing_score']
                    if specialty.place == None or \
                            budget_plan == None or \
                            budget_passing_score == None or \
                            paid_plan == None or \
                            paid_passing_score == None:
                        continue
                    var = Variant.objects.create(university=university,
                                                 specialty=specialty,
                                                 department=variant['department'],
                                                 education_type=variant['level'],
                                                 budget_plan=int(budget_plan),
                                                 budget_passing_score=int(budget_passing_score),
                                                 paid_plan=int(paid_plan),
                                                 paid_passing_score=int(paid_passing_score),
                                                 cost=variant['cost'],
                                                 rating=None,
                                                 applicants=[])
                    var.subjects.set(subjects)

        universities = pd.read_csv('universities_rating.csv', delimiter='\t')
        for index, row in universities.iterrows():
            university = University.objects.get(yandex_id=row.yandex_id)
            if row.place == -1:
                university.place = None
            else:
                university.place = int(row.place)
            university.save()

        for variant in Variant.objects.all():
            if variant.university.place != None:
                variant.rating = math.log(variant.university.place * variant.specialty.place)
                variant.save()
