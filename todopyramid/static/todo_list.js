$(function() {

    // Compete a todo task when the link is clicked
    $("a.todo-complete").click(function(e) {
        e.preventDefault();
        var todo_id = $(this).closest('ul').attr('id');
        var task = $(this).closest('tr');
        var task_name = task.children().first().text();
        bootbox.confirm("Delete '" + task_name + "'?", function(complete_item) {
            if (complete_item) {
                $.getJSON(
                    '/delete.task',
                    {'id': todo_id},
                    function(json) {
                        if (json) {
                            sid = "#" + todo_id;
                            task.remove();
                        }
                    }
                );
            }
        });
    });

});
