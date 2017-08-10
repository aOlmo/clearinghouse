def customizable_strings(request):
  from django.conf import settings
  return {
    "TESTBED": settings.TESTBED,
    "TESTBED_URL": settings.TESTBED_URL,
    "TESTBED_DEVELOPERS_MAIL": settings.TESTBED_DEVELOPERS_MAIL,
    "TESTBED_USERS_MAIL": settings.TESTBED_USERS_MAIL,
    "CLEARINGHOUSE": settings.CLEARINGHOUSE,
    "CLEARINGHOUSE_URL": settings.CLEARINGHOUSE_URL,
    "DEMOKIT": settings.DEMOKIT,
  }
