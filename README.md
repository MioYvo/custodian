# Custodian

Auto backup mysql db to cloud by [rclone](https://rclone.org/).

### deploy 

* docker-compose

  ```yaml
  version: "3.7"
  
  services:
      maria:
      image: mariadb
      # image: mysql
      restart: always
      # ports:
      #  - "12345:3306"
      volumes:
        - /data/maria:/var/lib/mysql
      environment:
        TZ: Asia/Shanghai
        MYSQL_USER_FILE: /run/secrets/db_user
        MYSQL_PASSWORD_FILE: /run/secrets/db_pass
        MYSQL_DATABASE_FILE: /run/secrets/db_name
        MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_root_pass
      secrets:
        - db_root_pass
        - db_user
        - db_pass
        - db_name
    
    custodian:
      image: custodian
      restart: always
      volumes:
        - /data/backup:/custodian/backup
      environment:
        MARIA_USER_FILE: /run/secrets/db_user
        MARIA_PASS_FILE: /run/secrets/db_pass
        MARIA_DB_FILE: /run/secrets/db_name
        MARIA_HOST: 'maria'
        MARIA_PORT: 3306
        hour: "3,15"
        access_key_id: "access_key_id"
        secret_access_key: "secret_access_key"
        endpoint: "oss-cn-hangzhou.aliyuncs.com
        run_once_immediately: 0
        run_immediately: 0
        max_files: 10
        TABLES: "tableA tableB tableC"
        TZ: Asia/Shanghai
      secrets:
        - db_user
        - db_pass
        - db_name
      logging:
        options:
          max-size: "10m"
          max-file: "1"
          
  secrets:
    db_root_pass:
      file: /etc/db_root_pass
  
    db_user:
      file: /etc/db_user
  
    db_pass:
      file: /etc/db_pass
  
    db_name:
      file: /etc/db_name
  ```

