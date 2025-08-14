from app import app, socketio

if __name__ == '__main__':
    # Run on port 8080 for Replit compatibility
    socketio.run(app, host='0.0.0.0', port=8080, debug=True, use_reloader=False, log_output=False)
