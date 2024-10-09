git clone https://github.com/wfcommons/WfFormat.git
python WfFormat/tools/wfcommons-migrate-instance.py $1
find $1/ -type f -exec sed -i 's/"coreCount": 0$/"coreCount": 1/g' {} \;
