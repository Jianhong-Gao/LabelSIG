import os
from datetime import datetime, timedelta
from .Comtrade import ComtradeReader

def format_datetime(dt: datetime) -> str:
    date_str = dt.strftime('%Y%m%d_%H%M%S')
    milliseconds_str = str(dt.microsecond // 1000).zfill(3)
    formatted_str = f'{date_str}_{milliseconds_str}'
    return formatted_str

def read_comtrade(base_filepath: str)-> ComtradeReader:
    """
    :param base_filepath: Base filepath without extensions (e.g., 'data/PSCAD')
    """
    cfg_filepath = base_filepath + '.cfg'
    dat_filepath = base_filepath + '.dat'
    # Check if the files exist
    if not os.path.exists(cfg_filepath) or not os.path.exists(dat_filepath):
        raise Exception("CFG and/or DAT files not found")
    # Create a ComtradeReader instance and load the CFG file
    comtrade_reader = ComtradeReader()
    comtrade_reader.load(cfg_filepath)
    return comtrade_reader


def get_info_comtrade(path_file_base=None):
    comtrade_reader = read_comtrade(path_file_base)
    start_timestamp = comtrade_reader.start_timestamp
    trigger_timestamp = comtrade_reader.trigger_timestamp
    sampling_rate = comtrade_reader.sampling_rate
    total_samples = comtrade_reader.total_samples
    # 计算两个日期时间对象之间的差异
    difference = trigger_timestamp - start_timestamp
    # 获取总秒数
    seconds_difference = difference.total_seconds()
    trigger_moment = int(seconds_difference*sampling_rate)
    info_comtrade={'start_timestamp':start_timestamp,
                   'trigger_timestamp':trigger_timestamp,
                   'sampling_rate':sampling_rate,
                   'total_samples':total_samples,
                   'trigger_moment':trigger_moment}
    return info_comtrade

def get_index_fault_moment(comtrade_reader:ComtradeReader)->int:
    trigger_timestamp = comtrade_reader.trigger_timestamp
    sampling_rate = comtrade_reader.sampling_rate
    # 计算两个日期时间对象之间的差异
    difference = trigger_timestamp
    # 获取总秒数
    seconds_difference = difference.total_seconds()
    index_difference = int(seconds_difference*sampling_rate)
    return index_difference


def process_analog_data(diff_U0, I0, index_fault_moment, length_one_cycle):
    length_waves = 6
    index_fault_moment = index_fault_moment
    channel_index_init=list(range(0,len(diff_U0)))
    if index_fault_moment-length_one_cycle<0:
        start_channel_index=0
    else:
        start_channel_index=index_fault_moment-length_one_cycle
    if start_channel_index+length_one_cycle*length_waves>channel_index_init[-1]:
        end_channel_index=channel_index_init[-1]
    else:
        end_channel_index=start_channel_index+length_one_cycle*length_waves
    channel_index = list(range(start_channel_index,end_channel_index))
    # 使用切片直接得到需要的电压和电流
    channel_voltage = diff_U0[start_channel_index:end_channel_index]
    channel_current = I0[start_channel_index:end_channel_index]
    return channel_voltage, channel_current, channel_index

def find_id_of_U0_I0(analog_channel_ids):
    nickname_U0=['UZ','Uz','U0','Uo','VefZ']
    nickname_I0=['IZ','Iz','I0']
    id_U0,id_I0=None,None
    for i,channel_name in enumerate(analog_channel_ids):
            for name_U0 in nickname_U0:
                if name_U0 in channel_name :
                        id_U0 = i
            for name_I0 in nickname_I0 :
                if name_I0 in channel_name and '(Id)' not in channel_name:
                    id_I0 = i
    if id_U0 is not None and id_I0 is not None:
        return id_U0,id_I0
    else:
        return None


def update_comtrade_trigger_time(path_raw: str,orig_name:str, trigger_timestamp: datetime):
    cfg_filepath = os.path.join(path_raw,orig_name) + '.cfg'
    dat_filepath = os.path.join(path_raw,orig_name) + '.dat'
    new_name=orig_name
    target_filepath = os.path.join(path_raw, new_name)
    new_cfg_filepath = target_filepath + '.cfg'
    new_dat_filepath = target_filepath +'.dat'

    # Check if the files exist
    if not os.path.exists(cfg_filepath) or not os.path.exists(dat_filepath):
        raise Exception("CFG and/or DAT files not found")

    # Create a ComtradeReader instance and load the CFG file
    comtrade_reader = ComtradeReader()
    comtrade_reader.load(cfg_filepath)

    # Create a ComtradeWriter instance
    comtrade_writer = ComtradeWriter(
        new_cfg_filepath,
        start=comtrade_reader.start_timestamp,
        trigger=trigger_timestamp,
        station_name=comtrade_reader.station_name,
        rec_dev_id=comtrade_reader.rec_dev_id,
        rev_year=comtrade_reader.rev_year,
        frequency=comtrade_reader.frequency,
        timemult=comtrade_reader.cfg.timemult,
        nrates=comtrade_reader.cfg.nrates,
        sampling_rate=comtrade_reader.sampling_rate
    )

    for i in range(comtrade_reader.n_analog_channels):
        comtrade_writer.add_analog_channel(
            id=comtrade_reader.analog_channel_ids[i],
            ph=comtrade_reader.analog_phases[i],
            ccbm=comtrade_reader.analog_ccbms[i],
            uu=comtrade_reader.analog_uu[i],
            a=comtrade_reader.analog_a[i],
            b=comtrade_reader.analog_b[i],
            skew=comtrade_reader.analog_skew[i],
            min=comtrade_reader.analog_min[i],
            max=comtrade_reader.analog_max[i],
            primary=comtrade_reader.analog_primary[i],
            secondary=comtrade_reader.analog_secondary[i],
            PS=comtrade_reader.analog_PS[i]
        )

    for i in range(len(comtrade_reader.time)):
        analog = [channel[i] for channel in comtrade_reader.analog]
        comtrade_writer.add_sample_record_new(comtrade_reader.time[i], analog, [])

    # Finalize the writing of the new file
    comtrade_writer.finalize()
    if cfg_filepath!=new_cfg_filepath:
        os.remove(cfg_filepath)
        os.remove(dat_filepath)
    return new_name

def update_comtrade(fault_trigger=None,path_raw=None,orig_name=None):
    comtrade_reader = read_comtrade(os.path.join(path_raw,orig_name))
    start_timestamp = comtrade_reader.start_timestamp
    sampling_rate = comtrade_reader.sampling_rate
    time_interval = (fault_trigger) / sampling_rate
    trigger_timestamp = start_timestamp + timedelta(seconds=time_interval)
    new_name=update_comtrade_trigger_time(path_raw=path_raw, orig_name=orig_name, trigger_timestamp=trigger_timestamp)
    return new_name


def delete_specific_channels(path_raw: str, orig_name: str, analog_channel_ids: list, status_channel_ids: list):
    cfg_filepath = os.path.join(path_raw, orig_name) + '.cfg'
    dat_filepath = os.path.join(path_raw, orig_name) + '.dat'

    # Check if the files exist
    if not os.path.exists(cfg_filepath) or not os.path.exists(dat_filepath):
        raise Exception("CFG and/or DAT files not found")

    # Create a ComtradeReader instance and load the CFG file
    comtrade_reader = ComtradeReader()
    comtrade_reader.load(cfg_filepath)

    # Create a temporary ComtradeWriter instance with the same metadata as the original
    tmp_cfg_filepath =os.path.join(path_raw, orig_name)+ '_tmp'+ '.cfg'
    tmp_dat_filepath = os.path.join(path_raw, orig_name) + '_tmp' + '.dat'
    comtrade_writer = ComtradeWriter(
        tmp_cfg_filepath,
        start=comtrade_reader.start_timestamp,
        trigger=comtrade_reader.trigger_timestamp,
        station_name=comtrade_reader.station_name,
        rec_dev_id=comtrade_reader.rec_dev_id,
        rev_year=comtrade_reader.rev_year,
        frequency=comtrade_reader.frequency,
        timemult=comtrade_reader.cfg.timemult,
        nrates=comtrade_reader.cfg.nrates,
        sampling_rate=comtrade_reader.sampling_rate
    )

    for i in range(comtrade_reader.n_analog_channels):
        # Only add analog channels which are not in the analog_channel_ids list
        if comtrade_reader.analog_channel_ids[i] not in analog_channel_ids:
            comtrade_writer.add_analog_channel(
                id=comtrade_reader.analog_channel_ids[i],
                ph=comtrade_reader.analog_phases[i],
                ccbm=comtrade_reader.analog_ccbms[i],
                uu=comtrade_reader.analog_uu[i],
                a=comtrade_reader.analog_a[i],
                b=comtrade_reader.analog_b[i],
                skew=comtrade_reader.analog_skew[i],
                min=comtrade_reader.analog_min[i],
                max=comtrade_reader.analog_max[i],
                primary=comtrade_reader.analog_primary[i],
                secondary=comtrade_reader.analog_secondary[i],
                PS=comtrade_reader.analog_PS[i]
            )

    # Assuming that the ComtradeReader class provides similar methods for status channels as it does for analog channels
    for i in range(comtrade_reader.n_status_channels):
        # Only add status channels which are not in the status_channel_ids list
        if comtrade_reader.status_channel_ids[i] not in status_channel_ids:
            comtrade_writer.add_status_channel(
                # Assuming similar attributes/methods exist for status channels as they do for analog channels
                # Adjust this part based on actual methods/attributes available for status channels
            )

    for i in range(len(comtrade_reader.time)):
        analog = [channel[i] for idx, channel in enumerate(comtrade_reader.analog) if comtrade_reader.analog_channel_ids[idx] not in analog_channel_ids]
        status = [channel[i] for idx, channel in enumerate(comtrade_reader.status) if comtrade_reader.status_channel_ids[idx] not in status_channel_ids]  # Assuming status data is structured similarly
        comtrade_writer.add_sample_record_new(comtrade_reader.time[i], analog, status)

    # Finalize the writing of the new file
    comtrade_writer.finalize()

    # Replace original files with modified files
    os.remove(cfg_filepath)
    os.remove(dat_filepath)
    os.rename(tmp_cfg_filepath, cfg_filepath)
    os.rename(tmp_dat_filepath, dat_filepath)


def get_channels_comtrade(path_file_base=None):
    comtrade_reader = read_comtrade(path_file_base)
    analog_channel_values = comtrade_reader.analog
    status_channel_values = comtrade_reader.status
    analog_channel_ids = comtrade_reader.analog_channel_ids
    status_channel_ids = comtrade_reader.status_channel_ids
    analog_uu = comtrade_reader.analog_uu

    # 分类电流和电压通道
    current_channel_ids = []
    voltage_channel_ids = []
    current_channel_values = []
    voltage_channel_values = []

    for idx, unit in enumerate(analog_uu):
        if unit in ["A", "kA", "mA"]:
            current_channel_ids.append(analog_channel_ids[idx])
            current_channel_values.append(analog_channel_values[idx])
        elif unit in ["V", "kV", "mV"]:
            voltage_channel_ids.append(analog_channel_ids[idx])
            voltage_channel_values.append(analog_channel_values[idx])
    return {
        'analog_channel_ids': analog_channel_ids,
        'status_channel_ids': status_channel_ids,
        'analog_channel_values': analog_channel_values,
        'status_channel_values': status_channel_values,
        'current_channel_ids': current_channel_ids,
        'voltage_channel_ids': voltage_channel_ids,
        'current_channel_values': current_channel_values,
        'voltage_channel_values': voltage_channel_values
    }




