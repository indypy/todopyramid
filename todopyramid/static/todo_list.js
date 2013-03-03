$(function() {

    // Show the fancy version of the due date
    $('.due-date').each(function() {
        var due_date = $(this).text();
        var human_date = moment(due_date, "YYYY-MM-DD HH:mm:ss").calendar();
        $(this).text(human_date);
    });

    // Edit a task when the edit link is clicked in the actions dropdown
    $("a.todo-edit").click(function(e) {
        e.preventDefault();
        var todo_id = $(this).closest('ul').attr('id');
        $.getJSON(
            '/edit.task',
            {'id': todo_id},
            function(json) {
                if (json) {
                    edit_form = $('#task-form');
                    // Set the title to Edit
                    edit_form.find('h3').text('Edit Task');
                    $.each(json, function(k, v) {
                        // Set the value for each field from the returned json
                        edit_form.find('input[name="' + k + '"]').attr('value', v);
                        // Re-initialize the fancy tags input
                        if (k === 'tags') {
                            edit_form.find('input[name="tags"]').importTags(v);
                        }
                    });
                    edit_form.modal('show');
                }
            }
        );
    });

    // Make sure the task-form gets put back to a clean "add" on cancel of "edit"
    $('#task-form').on('hidden', function () {
        // Set the title back to add
        $(this).find('h3').text('Add Task');
        // Clear out the input values
        $(this).find('input').each(function () {
            $(this).attr('value', '');
        });
        // Clear out the fancy tags
        $(this).find('div.tagsinput .tag').each(function () {
            $(this).detach();
        });
    });

    // Compete a todo task when the link is clicked
    $("a.todo-complete").click(function(e) {
        e.preventDefault();
        var todo_id = $(this).closest('ul').attr('id');
        var task = $(this).closest('tr');
        var task_name = task.children().first().text();
        var confirm_text = "<p>Confirm completion of <b><i>" + task_name + "</i></b></p><p>This action is not reversible and your task will be <b>deleted</b></p>";
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
                            flash.html(flash.html() + "<b><i>" + task_name + "</i></b> was deleted");
                            flash.removeClass('hide');
                            flash.addClass('alert-error');
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
