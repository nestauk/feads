from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.core.mail import send_mail


'''Number of jury members to send emails to'''
N_USERS = 5


class SeparatedValuesField(models.TextField):
    #__metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token', ',')
        super(SeparatedValuesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return
        if isinstance(value, list):
            return value
        return value.split(self.token)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not value:
            return
        assert(isinstance(value, list) or isinstance(value, tuple))
        return self.token.join([str(s) for s in value])

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)


class DataScienceResource(models.Model):
    '''Each instance represents a dataset or method
    used by the Nesta data science team. The creation of a
    new object will lead to :obj:`N_USERS` members being emailed.
    The added bonus is that this is (of course) the Django ORM,
    so all of our data sources and methods are hand-audited in
    this way.
    '''
    title = models.CharField(max_length=200, unique=True)
    justification = models.CharField(max_length=1000, default="")
    creation_date = models.DateTimeField('Date created', auto_now_add=True,
                                         blank=True, editable=False)

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title


class DataScienceMethod(DataScienceResource):
    wikipedia_page = models.URLField()
    method_type = models.CharField(
        max_length=7,
        choices=(('NLP', 'Natural Language Processing'),
                 ('CLUSTER', 'Clustering'),
                 ('REG', 'Value prediction'),
                 ('ENRICH', 'Data enrichment'))
    )
    lay_description = models.TextField()


class DataSource(DataScienceResource):
    #field_list = SeparatedValuesField()
    sensitive_fields = SeparatedValuesField(blank=True,
                                            null=True,
                                            default="")
    link_to_description = models.URLField()
    where_stored = models.CharField(max_length=3,
                                    choices=(('LOC', 'Local file storage'),
                                             ('CLF', 'Cloud file storage'),
                                             ('CLD', 'Cloud database')))


class Implementation(models.Model):
    id = models.AutoField(primary_key=True)
    data_source = models.ForeignKey(DataSource,
                                    on_delete=models.CASCADE)
    data_science_method = models.ForeignKey(DataScienceMethod,
                                            on_delete=models.CASCADE)
    why_we_did_this = models.CharField(max_length=1000)
    what_we_are_not_doing = models.CharField(max_length=500,
                                             null=True,
                                             blank=True)
    projects = models.CharField(
        max_length=3,
        choices=(('SCO', 'Scottish innovation mapping'),
                 ('RWJ', 'Robert Woods Johnson Foundation'),
                 ('EUR', 'EURITO'))
        )

    active = models.BooleanField(default=True)
    approved = models.BooleanField(default=False, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        '''Save the object and email jury members'''
        super().save(*args, **kwargs)

        # Get the users, excluding the submitter
        users = User.objects.exclude(pk=self.user.pk).order_by('?').all()
        n_users = len(users)
        if n_users > N_USERS:
            n_users = N_USERS

        # Email all users
        sub = ('Ethics panel: new data science implementation '
               f'({self.data_science_method} on {self.data_source}) '
               'awaits approval.')
        frm = "Nesta Data Science Ethics"
        for user in users[:n_users]:
            msg = (f'Dear {user.username},<br><br>Please click '
                   f'<a href="http://127.0.0.1:8000/jury/{self.id}">'
                   'here to review</a>')
            send_mail(sub, msg, frm, [user.email], fail_silently=False)
            # Create a Decisions object for each member of the jury
            Decisions.objects.get_or_create(user=user, resource=self)

    def __unicode__(self):
        return f"{self.data_science_method} on {self.data_source}"

    def __str__(self):
        return f"{self.data_science_method} on {self.data_source}"


class Decisions(models.Model):
    '''Instances represent the individual decision of a
    jury member (characterised by :obj:`user`) on
    :obj:`DataScienceResource` :obj:`resource`'''
    comment = models.TextField(default=("Please enter a comment or "
                                        "reason for deferment."),
                               editable=False)
    decision = models.BooleanField(default=False, editable=False)
    creation_date = models.DateTimeField('Date created', auto_now_add=True,
                                         blank=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    implementation = models.ForeignKey(Implementation,
                                       on_delete=models.CASCADE)

    class Meta:
        '''Specify a pseudo primary/unique key as a combination.
        The implication here is that each user can only adjudicate
        on a resource once.'''
        unique_together = (("implementation", "user"),)
        verbose_name_plural = "Decisions"

    def __unicode__(self):
        return "Decision on {} by {}".format(self.implementation.id,
                                             self.user.username)

    def __str__(self):
        return "Decision on {} by {}".format(self.implementation.id,
                                             self.user.username)

    def save(self, *args, **kwargs):
        '''Save the :obj:`Decision`, and update the
        :obj:`DataScienceResource` if required.'''
        # Update the DataScienceResource if required
        if self.pk is not None:
            # Sum up the number of accepts (including our new decision)
            decisions = Decisions.objects.filter(implementation=self.implementation).all()
            n_accepts = sum(d.decision for d in decisions
                            if d != self) + int(self.decision)
            # If the maximum number of accepts has been reached, then
            # approve this DataScienceResource
            if n_accepts == len(decisions):
                dsr = Implementation.objects.filter(pk=self.implemenation.pk)
                dsr.update(approved=True, active=False)
        super().save(*args, **kwargs)
