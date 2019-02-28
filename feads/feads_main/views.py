from django.shortcuts import render
from django.shortcuts import redirect
from .models import Implementation
from .models import Decisions
from django.contrib.auth.decorators import login_required
import json


@login_required
def index(request, id, err_msg=""):
    '''View for jury decisions on the :obj:`DataScienceResource`
    defined by :obj:`title`'''
    # Get the DataScienceResource and Decisions data
    imp = Implementation.objects.get(id=id)
    decisions = Decisions.objects.filter(implementation=imp,
                                         user=request.user).first()
    # Develop the context dependent on previous decision feedback
    context = {"imp": imp, "allowed": True, "err_msg": err_msg}
    # If not decision has been found, it implies that the user is
    # a valid django user, but has not been assigned to this task
    if decisions is None:
        context["err_msg"] = "You are not on the jury for this decision."
        context["allowed"] = False
    # The user has been assigned to this task, so retrieve previous data
    else:
        context["previous_choice"] = decisions.decision
        context["previous_comment"] = decisions.comment
        decision_field = Decisions._meta.get_field('comment')
        # If the task is no longer active then say so
        if not imp.active:
            context["err_msg"] = "This issue has been closed."
        # Otherwise work out whether this user has provided previous feedback
        elif decisions.comment != decision_field.default:
            context["err_msg"] = ("Thank you for participating. "
                                  "You can continue to amend your feedback "
                                  "until the resource has been approved.")
    # Done
    return render(request, 'feads_main/index.html', context=context)


@login_required
def process_decision(request, id):
    '''Processes the POST request from jury decision invoked in
    :obj:`index`, by updating the relevant :obj:`Decisions` object
    (and inadvertently updating the :obj:`DataScienceResource` via
    the :obj:`Decisions.save` method)
    '''
    # Get the POST data (the user's decision and comment)
    _choice = request.POST.get('decision', '') == "approve"
    comment = request.POST.get('comment', '')
    # If the DataScienceResource is no longer active then say so
    imp = Implementation.objects.get(id=id)
    if not imp.active:
        return redirect("index", id=id)
    # Check whether the feedback is long enough to defer
    if (not _choice) and len(comment) < 30:
        return index(request, id,
                     ("In order to defer you must provide "
                      "at least 30 characters of feedback!"))
    # Update the :obj:`Decisions` object
    decisions = Decisions.objects.filter(implementation=imp,
                                         user=request.user).first()
    decisions.comment = comment
    decisions.decision = _choice
    decisions.save()
    return redirect("index", id=id)


def active_resources(request):
    '''Generate information for the summary table'''
    # # The following field is for identifying pending feedback
    # decision_field = Decisions._meta.get_field('comment')
    # # Generate one row per DataScienceResource
    imp_list = []
    for imp in Implementation.objects.all():
        row = dict(implementation=f"{imp.why_we_did_this}",
                   data_source=f"{imp.data_source.title}",
                   data_source_sens=f"{imp.data_source.sensitive_fields}",
                   data_source_just=f"{imp.data_source.justification}",
                   data_source_link=f"{imp.data_source.link_to_description}",
                   data_source_where=f"{imp.data_source.get_where_stored_display()}",
                   method=f"{imp.data_science_method.title}",
                   method_type=f"{imp.data_science_method.get_method_type_display()}",
                   method_wiki=f"{imp.data_science_method.wikipedia_page}",
                   method_layd=f"{imp.data_science_method.lay_description}",
                   approved=f"{imp.approved}")
        imp_list.append(row)

    #     n = 0  # Total number of decisions (including pending)
    #     approvals, comments = [], []
    #     for decision in Decisions.objects.filter(implementation=imp):
    #         n += 1
    #         # If the decision is pending
    #         if decision.comment == decision_field.default:
    #             continue
    #         approvals.append(decision.decision)
    #         comments.append(decision.comment)
    #     # Generate counts of approvals and deferrals
    #     counts = Counter(approvals)
    #     # Append the row data. Note that decision counts are presented
    #     # as percentages
    #     if n > 0:
    #         imp_list.append((imp, "{:3.0f}".format(100*counts[True]/n),
    #                          "{:3.0f}".format(100*counts[False]/n),
    #                          comments))
    
    
    # Done
    context = {"implementations": json.dumps(imp_list)}
    #context = {"imp_list": list(Implementation.objects.all())}
    return render(request, 'feads_main/active_resources.html', context=context)
