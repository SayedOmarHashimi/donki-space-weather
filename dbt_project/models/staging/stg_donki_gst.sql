with source as (

    select * from {{ source('donki_raw', 'raw_gst') }}

),

renamed as (

    select
        "gstID"                                       as gst_id,
        strptime("startTime", '%Y-%m-%dT%H:%MZ')       as start_time,
        link,
        "linkedEvents"                                  as linked_events,
        strptime("submissionTime", '%Y-%m-%dT%H:%MZ')  as submission_time,
        "versionId"                                     as version_id,
        "sentNotifications"                              as sent_notifications

    from source

)

select * from renamed