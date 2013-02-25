$(function() {

    // Compete a todo task when the link is clicked
    $("a.todo-complete").click(function(e) {
        e.preventDefault();
        var todo_id = $(this).closest('ul').attr('id');
        var task = $(this).closest('tr');
        var task_name = task.children().first().text();
        var confirm_text = "<p>Confirm completion of <i>" + task_name + "</i></p><p>This action is not reversible and your task will be <b>deleted</b></p>";
        bootbox.confirm(confirm_text, function(complete_item) {
            if (complete_item) {
                $.getJSON(
                    '/delete.task',
                    {'id': todo_id},
                    function(json) {
                        if (json) {
                            // Delete the row
                            task.remove();
                            // Display a confirmation message
                            var flash = $('div.alert.hide').clone();
                            flash.html(flash.html() + "The item '" + task_name + "' was deleted");
                            flash.removeClass('hide');
                            flash.addClass('alert-success');
                            $('#flash-messages').append(flash);
                            flash.show();
                            // Change the count on the page
                            var count = $('.count');
                            var new_count = parseInt(count.text(), 10) - 1;
                            count.text(new_count);
                            // Remove the table if we deleted the last item
                            if (new_count === 0) {
                                $('.table').hide();
                                $('#content').append('<p>All done, nice work!</p>');
                            }
                        }
                    }
                );
            }
        });
    });

});
