$(".ajax-form").submit(function( event ) {
//Intercept patch/delete forms and send the data via Ajax
	event.preventDefault();
	var formMethod = $(this).children('input[name="method"]').val()
	if (formMethod == 'DELETE'){
	  ajaxDelete(this);
	} else if (formMethod == 'PATCH') {
	  ajaxPatch(this);
	} else {
	  console.log('Unknown HTTP method')
	}
});

function ajaxDelete(formD){
//Ajax for delete requests
	$.ajax({
	  method: 'DELETE',
	  url:  $(formD).children('input[name="url"]').val(),
	  contentType: 'application/json',
	  success: function() {
			window.location.href=$(formD).children('input[name="redirect"]').val();
	  },
	  error: function(){
			alert('Unsuccessful deletion');
	  },
		processData: false,
	  data: JSON.stringify({
			"_csrf_token": $(formD).children('input[name="_csrf_token"]').val()
		})
	});
}

function ajaxPatch(formP){
//Ajax for patch requests
	$.ajax({
	  method: 'PATCH',
	  url:  $(formP).children('input[name="url"]').val(),
	  contentType: 'application/json',
	  success: function() {
			window.location.href=$(formP).children('input[name="redirect"]').val();
	  },
	  error: function(){
			alert('Unsuccessful update');
	  },
	  processData: false,
	  data: makePayload(formP)
	});
}

function makePayload(formP){
//Make payload for patch requests
	var attr = $(formP).children('textarea, input[type="text"]').serializeArray();
	var payload = {
		"_csrf_token": $(formP).children('input[name="_csrf_token"]').val(),
	  "data": {
		"type": $(formP).children('input[name="type"]').val(),
		"id": $(formP).children('input[name="id"]').val(),
		"attributes": attr
	  }
	}
	return JSON.stringify(payload);
}

function updateToggle(editButton){
//Toggle view for patch/delete forms
	$(editButton).siblings('.update-hide, .ajax-form').toggleClass('hidden')
	if ($(editButton).text() == 'Cancel'){
	  $(editButton).text($(editButton).val())
	} else {
	  $(editButton).text('Cancel')
	}
}
