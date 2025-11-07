from models import mongo

def clear_violations():
    try:
        # Use the existing MongoDB connection from Flask app
        result = mongo.db.violations.delete_many({})
        print(f'Successfully deleted {result.deleted_count} violations')
        return True
    except Exception as e:
        print(f'Error deleting violations: {str(e)}')
        return False

if __name__ == '__main__':
    clear_violations()