from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

from .models import DataScienceResource
from .models import Decisions
from .models import N_USERS


class DataScienceResourceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        '''Create users, super user and a test :obj:`DataScienceResource`'''
        # Create users and super users
        cls.super_user = User.objects.create_superuser(username="superuser",
                                                       password='12345',
                                                       email='some@one.com')
        cls.users = [User.objects.create_user(username="user{}".format(i),
                                              password='12345',
                                              email='some{}@one.com'.format(i))
                     for i in range(0, 20)]

        # Log the super user in and create the DataScienceResource
        cls.dsr = DataScienceResource(title="test model",
                                      description="a description",
                                      resource_type="METHOD",
                                      data_source="somewhere",
                                      data_location="someplace",
                                      user=cls.super_user)
        cls.dsr.save()
        super().setUpClass()

    def setUp(self):
        self.client = Client()

    def test_jury_size(self):
        '''Test number of users assigned to the decision:
        There should be fewer Decisions.objects than users,
        and the number should be equal to N_USERS
        '''
        decisions = Decisions.objects.filter(resource=self.dsr).all()
        self.assertLess(len(decisions), len(self.users))
        self.assertEqual(len(decisions), N_USERS)

    def test_table_after_feedback(self):
        '''Test the context has the correct
        properties after feedback'''
        response = self.client.get("")
        context = response.context["dsr_list"]
        self.assertEqual(len(context), 1)
        self.assertEqual(len(context[0]), 4)

    def test_index_user_access(self):
        '''Test the index context has the correct
        properties if the user has not been assigned to the task'''
        decisions = Decisions.objects.filter(resource=self.dsr).all()
        url = reverse("index", kwargs={"title": self.dsr.title})
        active_users = [d.user for d in decisions]
        for user in self.users:
            # Log in, and follow to page
            self.client.login(username=user.username,
                              password='12345')
            response = self.client.get(url)
            self.assertEqual(response.context["allowed"],
                             user in active_users)

    def test_decision_processing(self):
        '''Test that decisions are processed correctly'''
        # Iterate over active users
        decisions = Decisions.objects.filter(resource=self.dsr).all()
        url = reverse("process_decision", kwargs={"title": self.dsr.title})
        active_users = [d.user for d in decisions]
        for user in self.users:
            if user not in active_users:
                continue
            # Log in
            self.client.login(username=user.username,
                              password='12345')
            # Expect deferals to have large comments
            response = self.client.post(url,
                                        {'decision': 'defer', 'comment': ''})
            self.assertIn("30 characters", response.context['err_msg'])
            # Then approve
            response = self.client.post(url,
                                        {'decision': 'approve', 'comment': ''})
        # After all approvals, test that DataScienceResource
        # is no longer active
        dsr = DataScienceResource.objects.get(title=self.dsr.title)
        self.assertFalse(dsr.active)
        self.assertTrue(dsr.approved)
