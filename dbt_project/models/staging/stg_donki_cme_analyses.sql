with source as (

    select * from {{ source('donki_raw', 'raw_cme_analyses') }}

),

renamed as (

    select
        analysis_link,
        "activityID"                                       as cme_id,
        "isMostAccurate"                                    as is_most_accurate,
        strptime(time21_5, '%Y-%m-%dT%H:%MZ')               as time_21_5,
        latitude,
        longitude,
        "halfAngle"                                          as half_angle,
        speed,
        type,
        "featureCode"                                        as feature_code,
        "imageType"                                           as image_type,
        "measurementTechnique"                                as measurement_technique,
        note,
        "levelOfData"                                        as level_of_data,
        tilt,
        "minorHalfWidth"                                     as minor_half_width,
        "speedMeasuredAtHeight"                               as speed_measured_at_height,
        strptime("submissionTime", '%Y-%m-%dT%H:%MZ')         as submission_time

    from source

)

select * from renamed