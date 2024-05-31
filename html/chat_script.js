// Define functions in the global scope

// !!!!!!!!Change WEBSOCKET_URL to your websocket!!!!!!!!!!!
const WEBSOCKET_URL = 'wss://www.iamcalledcharlie.com/ws';

let socket; // Declare the WebSocket outside of the functions
let reconnectInterval = 1000; // Start with 1 second
const MAX_RECONNECT_INTERVAL = 30000; // Max interval 30 seconds
var persona = "";
console.log('set persona:', persona)


// This function should only be responsible for sending the selected persona
function sendPersona() {
    persona = document.getElementById('personaDropdown').value;
    console.log('set persona', persona);

    // Send the selected persona back to the server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: 'persona_selected',
            persona: persona
        }));
    }
    // Update the typing text span with the selected persona's name
    document.getElementById('typing-text').innerText = persona + ' is typing...';

    // Hide the dropdown after selection using classList to remove 'show' class
    document.getElementById('personaSelection').classList.remove('show');
}

// This function is called when 'select_persona' message is received
function showPersonaSelection() {
    // Use jQuery for consistency since it's used elsewhere in your script
    $('#personaSelection').addClass('show');
}

function showPersonaSelection() {
    // Use jQuery for consistency since it's used elsewhere in your script
    $('#personaSelection').addClass('show');
}


function showTypingIndicator() {
    $('#typing-container').show();
}

function hideTypingIndicator() {
    $('#typing-container').hide();
}



function initializeShoppingList() {
    $('#shopping-list-button').click(function() {
        $('#shopping-list-overlay').removeClass('hidden');
    });

    $('#close-shopping-list').click(function() {
        $('#shopping-list-overlay').addClass('hidden');
    });
}

function initializeRecipeBox() {
    $('#recipe-box-button').click(function() {
        // Request the user's recipes when they click the Recipe Box button
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'get_user_recipes' }));
        }
    });

    $('#close-recipe-box').click(function() {
        $('#recipe-box-overlay').addClass('hidden');
    });
}
function displayRecentMessages(messages) {
    messages.reverse().forEach(function(message) {
        var messageElement;

        // Check the 'MessageType' to determine if it's from the user or the bot
        if (message.MessageType === 'user') {
            messageElement = $('<div class="message user">').text('You: ' + message.Message);
        } else if (message.MessageType === 'bot') {
            messageElement = $('<div class="message bot">').text(persona + ': ' + message.Message);
        } else {
            messageElement = $('<div class="message">').text(message.Message); // Fallback for undefined MessageType
        }
        // Add the timestamp as a data attribute
        messageElement.attr('data-timestamp', message.Timestamp);

        $('#messages').append(messageElement);
    });

    $('#messages').scrollTop($('#messages')[0].scrollHeight); // Auto-scroll to the latest message
}

function displayMoreMessages(messages) {
    messages.forEach(function(message) {
        var messageElement;

        // Check the 'MessageType' to determine if it's from the user or the bot
        if (message.MessageType === 'user') {
            messageElement = $('<div class="message user">').text('You: ' + message.Message);
        } else if (message.MessageType === 'bot') {
            messageElement = $('<div class="message bot">').text(persona + ': ' + message.Message);
        } else {
            messageElement = $('<div class="message">').text(message.Message); // Fallback for undefined MessageType
        }

        // Add the timestamp as a data attribute
        messageElement.attr('data-timestamp', message.Timestamp);

        // Prepend the message at the beginning of the messages container
        $('#messages').prepend(messageElement);
    });

}


function getOldestMessageTimestamp() {
    // Get the first message in the container (which is the oldest due to reverse order)
    var oldestMessage = $('#messages .message:first');

    // Return its timestamp
    return oldestMessage.data('timestamp');
}


function initializeWebSocket() {
    if (!socket || socket.readyState === WebSocket.CLOSED) {
        socket = new WebSocket(WEBSOCKET_URL);

        socket.onopen = function() {
            
            var messageObject = {
                action: 'load_messages'
                
            };

            socket.send(JSON.stringify(messageObject));
            reconnectInterval = 1000; // Reset reconnect interval on successful connection
            
            // console.log('WebSocket connected!');
        };

        socket.onclose = function(event) {
            
            setTimeout(reconnectWebSocket, reconnectInterval);
            reconnectInterval = Math.min(reconnectInterval * 2, MAX_RECONNECT_INTERVAL); // Exponential backoff
            // console.log('WebSocket closed:', event);
        };


        socket.onmessage = function(event) {
            var msg = JSON.parse(event.data);
            // console.log('Received message:', msg);
        
            if (msg.action === 'ping') {
                // console.log('Received ping message');
                
                
                var pongMessage = {
                    action: 'pong'
                    
                };
            
                socket.send(JSON.stringify(pongMessage));
            
            } else if (msg.action === 'shopping_list_update') {
                updateShoppingListUI(msg.shoppingList);

            } else if (msg.action === 'recent_messages') {
                    displayRecentMessages(msg.messages);

                    
            } else if (msg.action === 'older_messages') {
                    displayMoreMessages(msg.messages);
    
            
            } else if (msg.action === 'user_recipes_list') {
                    displayUserRecipes(msg.recipes); // Function to handle displaying the recipes
                            
            } else if (msg.action === 'force_logout') {
                // Redirect to login page
                window.location.href = '/login'; // Adjust URL as needed
            
            
            } else if (msg.action === 'select_persona') {
                        // Call the function to show persona selection dropdown
                    showPersonaSelection();
    
            } else if (msg.action === 'redirect_login') {
                // Optionally display an alert or notification to the user
                alert('Your session is invalid. Please log in again.');
        
                // Redirect to the login page
                window.location.href = '/login';  // Adjust this URL as needed
                          
            
            } else if (msg.action === 'recipe_saved') {
                // Check if the recipe was successfully saved and show a notification
                if (msg.status === 'success') {
                    $('.save-recipe-button').text('Recipe Saved'); // Change button text
                    $('.save-recipe-button').addClass('recipe-saved-button'); // Add a new class for styling (optional)
                    $('.save-recipe-button').prop('disabled', true); // Disable the button
                    showNotificationBubble('Recipe saved');
                } else {
                    // Handle other statuses, like errors
                    showNotificationBubble('Failed to save recipe');
                }
            } else if (msg.action === 'recipe_printed') {
                // Extract the HTML-formatted recipe data
                var recipeHtml = msg.data;
            
                // Create a new window or an invisible iframe for printing
                var printWindow = window.open('', '_blank');
            
                // Set the document content for printing
                printWindow.document.write('<html><head><title>Print Recipe</title></head><body>');
                printWindow.document.write(recipeHtml);  // Insert the HTML-formatted recipe
                printWindow.document.write('</body></html>');
            
                //printWindow.document.close(); // Necessary for some browsers
            
                // Wait for the content to fully load
                printWindow.onload = function() {
                    // Open the print dialog
                    printWindow.print();
                    // Close the print window after printing (optional)
                    printWindow.close();
                };
                        
            
            } else {
                hideTypingIndicator();
                var messageElement;
                if (msg.type === 'recipe') {
                    messageElement = $('<div class="message-bubble recipe-message">'); // Add 'recipe-message' class
                    var messageContent = $('<div class="message-content">').html(msg.response);
                    // Create a Print button
                    var printButton = $('<button class="print-recipe-button" data-recipe-id="' + msg.recipe_id + '">Print Recipe</button>');
                   
                    // create a Save button
                    var saveButton = $('<button class="save-recipe-button" data-recipe-id="' + msg.recipe_id + '">Save Recipe</button>');
                    messageElement.append(messageContent, saveButton, printButton);

                } else if (msg.type === 'shopping_list') { // Check if message type is shopping list
                    messageElement = $('<div class="message-bubble shopping-list-message">'); // Use a different class for shopping list messages
                    var messageContent = $('<div class="message-content">').html(msg.response);
                    // You could add buttons or other elements specific to a shopping list here
                    var saveButton = $('<button class="save-shopping-list-button">Save Shopping List</button>');
                    messageElement.append(messageContent, saveButton);

               } else {
                    messageElement = $('<div class="message bot">').html(msg.response);
                }
                $('#messages').append(messageElement);
                $('#messages').scrollTop($('#messages')[0].scrollHeight);
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket Error:', error);
        };

        
    }
}

function sendMessage() {
    var message = $('#message-input').val();
    if (message.trim().length > 0) {
         if (socket.readyState === WebSocket.OPEN) {
            
            var messageObject = {
                action: 'chat_message',
                message: message
                
            };

            socket.send(JSON.stringify(messageObject));
            $('#message-input').val('');
            var userMessageElement = $('<div class="message user">').text('You: ' + message);
            $('#messages').append(userMessageElement);
            showTypingIndicator();
            $('#messages').scrollTop($('#messages')[0].scrollHeight);
        } else {
            console.error('WebSocket is not open. ReadyState:', socket.readyState);
        }
    }
}

$(document).ready(function() {
         initializeWebSocket();
         initializeShoppingList();
         initializeRecipeBox();


        // Initialize event listeners
        
        

    $('#send-button').click(sendMessage);
    $('#message-input').keypress(function(e) {
        if (e.which == 13) {
            sendMessage();
            return false; // Prevent form submission
        }
    });

    hideTypingIndicator();

    
    $(document).on('mouseenter', '.save-recipe-button', function() {
        // Check if the button is disabled
        if ($(this).prop('disabled')) {
            // If the button is disabled, it means the recipe is already saved
            
        } else {
            // If the button is not disabled, show the default tooltip
            $(this).append($('<span class="tooltip">Click to add this to your recipe box!</span>'));
        }
    }).on('mouseleave', '.save-recipe-button', function() {
        // Remove the tooltip when the mouse leaves the button
        $(this).find('.tooltip').remove();
    });

    $(document).on('click', '.save-recipe-button', function() {
        var recipeId = $(this).data('recipe-id')
        var messageContent = $(this).siblings('.message-content');
        
        if (messageContent.length) {
            var recipeContent = messageContent.text();
            

            if (socket && socket.readyState === WebSocket.OPEN) {
                var saveCommand = {
                    action: 'save_recipe',
                    content: recipeId
                    
                };
                socket.send(JSON.stringify(saveCommand));
                
                
            } else {
                console.error('WebSocket is not open.');
            
            }
        } else {
            console.error("No .message-content found alongside the Save Recipe button.");
        }
       
    });

    $(document).on('click', '.save-shopping-list-button', function() {
        var recipeId = $(this).data('recipe-id')
        var messageContent = $(this).siblings('.message-content');
        
        if (messageContent.length) {
            var recipeContent = messageContent.text();
            

            if (socket && socket.readyState === WebSocket.OPEN) {
                var saveCommand = {
                    action: 'save_recipe',
                    content: recipeId
                    
                };
                socket.send(JSON.stringify(saveCommand));
                
                
            } else {
                console.error('WebSocket is not open.');
            
            }
        } else {
            console.error("No .message-content found alongside the Save Recipe button.");
        }
       
    });
    $(document).on('click', '.print-recipe-button', function() {
        // console.log("print recipe clicked")
        var recipeId = $(this).data('recipe-id')
        var messageContent = $(this).siblings('.message-content');
        
        if (messageContent.length) {
            var recipeContent = messageContent.text();
            

            if (socket && socket.readyState === WebSocket.OPEN) {
                var PrintCommand = {
                    action: 'print_recipe',
                    content: recipeId
                    
                };
                socket.send(JSON.stringify(PrintCommand));
                
                
            } else {
                console.error('WebSocket is not open.');
            
            }
        } else {
            console.error("No .message-content found alongside the Save Recipe button.");
        }
    
    
    });
    
    
    window.addEventListener('load', () => {
        function updateOnlineStatus() {
            if (navigator.onLine) {
                reconnectWebSocket(); // Attempt to reconnect WebSocket if not connected
            } 
        }
    
        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
    });
    
    
    document.addEventListener("visibilitychange", handleVisibilityChange);

    
    document.querySelector('.hamburger-menu').addEventListener('click', function() {
        document.querySelector('.options-menu').classList.toggle('show');
    });

    document.getElementById('logout').addEventListener('click', function() {
        sessionStorage.clear();
        window.location.href = '/login'; // Adjust the URL as needed
    });

    document.getElementById('messages').addEventListener('scroll', function() {
        if (this.scrollTop === 0) {
            // console.log('Reached top of messages');
            loadMoreMessages();
        }
    });
});

function addToShoppingList(item) {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({'action': 'add_to_shopping_list', 'item': item}));
    } else {
        console.error('WebSocket is not open. ReadyState:', socket.readyState);
    }
}

function removeItemFromShoppingList(item) {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({'action': 'remove_from_shopping_list', 'item': item}));
    }
}

function updateShoppingListUI(shoppingList) {
    $('#shopping-list').empty();
    shoppingList.forEach(function(item) {
        var listItem = $('<li></li>').text(item.name);
        if (item.checked) {
            listItem.addClass('checked');
        }
        $('#shopping-list').append(listItem);
    });
}

function loadMoreMessages() {
    var lastMessageTimestamp = getOldestMessageTimestamp();
    if (lastMessageTimestamp) {
        socket.send(JSON.stringify({
            action: 'load_more_messages',
            last_loaded_timestamp: lastMessageTimestamp
        }));
    }
}



function displayUserRecipes(recipes) {
    const recipeBox = $('#recipe-box');
    recipeBox.empty(); // Clear the existing recipes if any

    recipes.forEach(function(recipe) {
        // Create list item container
        var recipeItem = $('<li></li>').addClass('recipe-item');
        
        // Create the recipe title span
        var recipeTitle = $('<span></span>').addClass('recipe-title').text(recipe.title);
        
        // Create the remove button
        var removeButton = $('<button></button>').addClass('remove-recipe-button').text('Remove');
        
        // Attach click event to the recipe title
        recipeTitle.click(function() {
            // console.log("Recipe clicked:", recipe.recipe_id);
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ action: 'print_recipe', content: recipe.recipe_id }));
            }
        });
        
        // Attach click event to the remove button
        removeButton.click(function() {
            // console.log("Remove clicked for recipe:", recipe.recipe_id);
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ action: 'remove_recipe', content: recipe.recipe_id }));
            }
            recipeItem.remove(); // Remove the item from the DOM
        });
        
        // Append the title and button to the list item container
        recipeItem.append(recipeTitle);
        recipeItem.append(removeButton);
        
        // Append the item container to the list
        recipeBox.append(recipeItem);
    });

    $('#recipe-box-overlay').removeClass('hidden'); // Show the recipe box overlay
}

function showOverlay(title, content) {
    const overlay = $('<div class="overlay"></div>');
    const overlayContent = $('<div class="overlay-content"></div>');
    overlayContent.append($('<h2></h2>').text(title), $('<p></p>').text(content), $('<button>Close</button>').click(function() { overlay.remove(); }));
    overlay.append(overlayContent);
    $('body').append(overlay);
}
 
function logout() {
    sessionStorage.clear();
    window.location.href = '/login'; // Adjust the URL as needed
}
function showNotificationBubble(message) {
    var bubble = $('<div class="notification-bubble">' + message + '</div>');
    
    $('body').append(bubble);
    bubble.fadeIn(200).delay(3000).fadeOut(200, function() {
        $(this).remove(); // Remove the bubble from the DOM after it fades out
    });
}
function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
        // console.log("Page is now visible");
        // Reconnect WebSocket if needed
        if (!socket || socket.readyState === WebSocket.CLOSED) {
            initializeWebSocket();
        }
    } else if (document.visibilityState === 'hidden') {
        // console.log("Page is now hidden");
        // Additional actions when the page is not visible (if needed)
    }
}

function reconnectWebSocket() {
    if (!socket || socket.readyState === WebSocket.CLOSED) {
        initializeWebSocket();
    }
}