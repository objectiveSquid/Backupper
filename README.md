# Backupper
## Prerequisites
You must install the requirements from `requirements.txt` as such:
```sh
python3 -m pip install -r requirements.txt
```

## Create a backup
```sh
python3 make_backup.py [-h] [--ignore_list IGNORE_LIST] [--dont_copy_exif] [--dont_copy_timestamps] backup_directory backup_list
```

## Restore a backup
```sh
python3 restore_backup.py [-h] [--dont_copy_exif] [--dont_copy_timestamp] backup_directory
```

## Formats
### Backup lists
A backup list could look like this, with the colon seperating the source path and the destination in the backup:
```
/home/user/Downloads:Downloads
/home/user/Scripts:Scripts
/etc:etc
/lib:libraries
```

### Ignore lists
An ignore list is a list of regex expression, which if matched with a file path, the path is not backed up.
They should look like this:
```
.*__pycache__.*
/etc/emacs/.*
/home/user/Scripts/unimportant_script.sh
```
