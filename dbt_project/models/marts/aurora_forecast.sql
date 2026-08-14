with kp_readings as (

    select * from {{ ref('stg_donki_gst_kp_index') }}

),

latest_reading as (

    select
        gst_id,
        observed_time,
        kp_index,
        source

    from kp_readings

    qualify row_number() over (order by observed_time desc) = 1

)

select
    gst_id,
    observed_time                                    as last_observed_time,
    kp_index                                          as last_kp_index,
    source,

    case
        when kp_index >= 7 then 'high'
        when kp_index >= 5 then 'moderate'
        else 'low'
    end                                                as aurora_chance,

    current_timestamp                                 as calculated_at

from latest_reading