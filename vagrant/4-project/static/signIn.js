function iniGAuth() {
// Initialize googleAuth object
  console.log('Initalizing googleAuth object')
  gapi.load('auth2', function() {
	auth2 = gapi.auth2.init({
	  client_id: '956019190263-o6a7gusm85fhipgr316rtq2ck41dj7ht.apps.googleusercontent.com',
	});
  });
 }

$('#signinButton').click(function() {
// On click open the google login window
// On successful login, pass authResult to the specified function
  auth2.grantOfflineAccess().then(signInCallback);
});

function signInCallback(authResult) {
  if (authResult['code']) {
	$('#signinButton').attr('style', 'display: none');
	// Send the one-time code to the server
	console.log('Sending one-time code to the server...')
	$.ajax({
	  method: 'POST',
	  url: 'http://localhost:5000/gconnect',
	  contentType: 'application/json',
	  success: function(info) {
		$('#flash-msg').html('Login successful! <br> Hello ' + info.username + '<br> Redirecting...');
		if (info.new_user) {
		  setTimeout(function(){window.location.href='/users/{}/new'.replace('{}', info.user_id);}, 2000);
		} else {
		  setTimeout(function(){window.location.href='/users/{}'.replace('{}', info.user_id);}, 2000);
		}
	  },
	  error: function(jqXHR, textStatus, errorThrown){
		alert('Unsuccessful sign-in');
		console.log($.parseJSON(jqXHR.responseText)['error-msg']);
	  },
	  processData: false,
	  data: JSON.stringify({
		"_csrf_token": $('meta[name=_csrf_token]').attr("content"),
		"auth_code": authResult['code']
	  })

	});
  } else {
	console.log('One-time code missing in authResult');
  }
}

$('#signoutButton').click(function() {
	// Sign out user
	$.ajax({
	  method: 'POST',
	  url: 'http://localhost:5000/gdisconnect',
	  contentType: 'application/json',
	  success: function() {window.location.href='/';},
	  error: function(jqXHR, textStatus, errorThrown){
		alert('Unsuccessful sign-out');
		console.log($.parseJSON(jqXHR.responseText)['error-msg']);
	  },
	  processData: false,
	  data: JSON.stringify({
		"_csrf_token": $('meta[name=_csrf_token]').attr("content"),
	  })
	});
})

